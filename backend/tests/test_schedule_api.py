"""HTTP contracts with synthetic data; database cases use isolated PostgreSQL only."""
import asyncio

from datetime import date, datetime, time, timezone
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.api.schedule import get_schedule_service
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.models import Game, SourceArtifact, Team
from app.schemas.schedule import GameResponse, Policy, ScheduleMeta, ScheduleResponse, SeasonsMeta, SeasonsResponse
from app.services.schedule import GameNotFound

pytestmark = pytest.mark.api


def application():
    return create_app(Settings(db_host='synthetic.invalid',db_name='nfl_research_test',db_user='synthetic',db_password='SYNTHETIC_ONLY'))


@pytest.fixture
def client(api_game):
    service = Mock()
    service.seasons.return_value = SeasonsResponse(data=[],meta=SeasonsMeta(missing_seasons=[2024,2025,2026],returned_count=0))
    from app.services.schedule import game_view
    service.game.return_value = GameResponse(data=game_view(api_game),meta=Policy())
    service.schedule.side_effect = lambda season, filters: ScheduleResponse(data=[],meta=ScheduleMeta(
        season=season,filters=filters,returned_count=0,season_coverage=[]))
    app = application()
    app.dependency_overrides[get_schedule_service] = lambda: service
    with TestClient(app) as http:
        yield http, service


def test_seasons_json(client):
    http,service = client
    response = http.get('/api/seasons')
    assert response.status_code == 200
    assert set(response.json()) == {'data','meta'}
    assert response.json()['meta']['missing_seasons'] == [2024,2025,2026]
    service.seasons.assert_called_once()


@pytest.mark.parametrize('query', ['season_type=REG&week=1','season_type=POST&round=WC','season_type=POST&week=20&round=DIV','season_type=REG'])
def test_valid_filters_empty_results(client,query):
    response = client[0].get('/api/seasons/2026/schedule?'+query)
    assert response.status_code == 200 and response.json()['data'] == []
    assert response.json()['meta']['returned_count'] == 0


@pytest.mark.parametrize('path', [
    '/api/seasons/2023/schedule?season_type=REG', '/api/seasons/2027/schedule?season_type=REG',
    '/api/seasons/bad/schedule?season_type=REG','/api/seasons/2026/schedule',
    '/api/seasons/2026/schedule?season_type=ALL','/api/seasons/2026/schedule?season_type=REG&week=19',
    '/api/seasons/2026/schedule?season_type=POST&week=1','/api/seasons/2026/schedule?season_type=POST&week=20&round=WC',
    '/api/seasons/2026/schedule?season_type=REG&round=SB','/api/seasons/2026/schedule?season_type=POST&round=bad',
    '/api/seasons/2026/schedule?season_type=REG&week=abc','/api/seasons/2026/schedule?season_type=REG&week=0',
    '/api/seasons/2026/schedule?season_type=REG&week=1&week=2',
    '/api/seasons/2026/schedule?season_type=REG&surprise=SECRET_VALUE',
    '/api/games/not-a-uuid', '/api/seasons?surprise=SECRET_VALUE',
    '/api/games/00000000-0000-0000-0000-000000000001?surprise=SECRET_VALUE',
])
def test_invalid_request(path):
    # Async transport avoids a blocking portal for validation-only requests.
    # No sync route or database work is executed for these invalid requests.
    app = application()
    async def unused_service():
        return None
    app.dependency_overrides[get_schedule_service] = unused_service
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as http:
            return await http.get(path)
    response = asyncio.run(request())
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'
    assert response.json()['error']['details']
    assert 'SECRET_VALUE' not in response.text


def test_game_json_and_not_found(client,api_game):
    http,service = client
    response = http.get(f'/api/games/{api_game.id}')
    assert response.status_code == 200
    data = response.json()['data']
    assert data['id'] == str(api_game.id)
    assert data['status'] == 'UNKNOWN' and data['reported_home_score'] == 0
    assert data['provenance']['origin_status'] == 'DECLARED'
    assert data['score_finality'] == 'UNVERIFIED'
    service.game.assert_called_with(api_game.id)
    service.game.side_effect = GameNotFound()
    response = http.get(f'/api/games/{uuid4()}')
    assert response.status_code == 404 and response.json()['error']['code'] == 'GAME_NOT_FOUND'


@pytest.mark.parametrize('path', ['/api/seasons','/api/seasons/2026/schedule?season_type=REG','/api/games/00000000-0000-0000-0000-000000000001'])
def test_database_failure_is_sanitized(path):
    app = application()
    session = Mock()
    session.execute.side_effect = session.scalar.side_effect = session.scalars.side_effect = OperationalError(
        'PRIVATE SQL',{'password':'PRIVATE_CREDENTIAL'},Exception('PRIVATE CONNECTION'))
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as http:
        response = http.get(path)
    assert response.status_code == 503
    assert response.json() == {'error':{'code':'DATABASE_UNAVAILABLE','message':'Schedule data is temporarily unavailable','details':[]}}
    assert 'PRIVATE' not in response.text
    session.commit.assert_not_called()
    session.flush.assert_not_called()


@pytest.mark.parametrize('method', ['post','put','patch','delete'])
def test_schedule_is_read_only(method):
    async def request():
        async with AsyncClient(transport=ASGITransport(app=application()),base_url='http://test') as http:
            return await http.request(method,'/api/seasons/2026/schedule?season_type=REG')
    response = asyncio.run(request())
    assert response.status_code == 405
    assert response.json()['error']['code'] == 'METHOD_NOT_ALLOWED'
    assert 'GET' in response.headers['allow']


@pytest.mark.database
def test_postgresql_schedule_end_to_end(db_session):
    """Synthetic 5-game DB dataset: older years, no 2026 POST, null and tied kickoffs."""
    home, away = Team(code='AAA',name='Synthetic Home'),Team(code='BBB',name='Synthetic Away')
    artifact = SourceArtifact(provider='nflverse',artifact_path='synthetic://api-fixture',sha256='a'*64,byte_size=0,origin_status='DECLARED')
    db_session.add_all([home,away,artifact]);db_session.flush()
    ids = [UUID(int=n) for n in range(1,6)]
    for index,(year,stage,week,kind,kickoff,score) in enumerate([
        (2024,'REG',1,'REG',None,0), (2025,'POST',19,'WC',None,7),
        (2026,'REG',9,'REG',datetime(2026,11,8,18,tzinfo=timezone.utc),0),
        (2026,'REG',9,'REG',None,None),
        (2026,'REG',9,'REG',datetime(2026,11,8,18,tzinfo=timezone.utc),7),
    ]):
        db_session.add(Game(id=ids[index],provider='nflverse',source_game_id=f'synthetic-{index}',
            season=year,season_type=stage,week=week,game_type=kind,home_team_id=home.id,away_team_id=away.id,
            source_home_team='AAA',source_away_team='BBB',source_gameday=date(year,11,8) if kickoff else None,
            source_gametime=time(13) if kickoff else None,scheduled_kickoff_utc=kickoff,
            reported_home_score=score,reported_away_score=score,status='UNKNOWN',source_artifact_id=artifact.id,
            source_record_sha256='b'*64))
    # Unrelated provider must never leak into schedule results.
    other_artifact = SourceArtifact(provider='other',artifact_path='synthetic://other',sha256='c'*64,byte_size=0)
    db_session.add(other_artifact);db_session.flush()
    db_session.add(Game(provider='other',source_game_id='other',season=2026,season_type='POST',game_type='WC',week=19,
        home_team_id=home.id,away_team_id=away.id,source_home_team='AAA',source_away_team='BBB',
        source_artifact_id=other_artifact.id,source_record_sha256='d'*64))
    db_session.flush()
    app = application()
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as http:
        seasons = http.get('/api/seasons').json()['data']
        assert [s['season'] for s in seasons] == [2024,2025,2026]
        assert seasons[2]['coverage'][1]['game_count'] == 0
        assert seasons[2]['coverage'][0]['missing_score_pairs'] == 1
        assert seasons[2]['coverage'][0]['unknown_status_games'] == 3
        assert seasons[2]['coverage'][0]['unverified_origin_games'] == 3
        response = http.get('/api/seasons/2026/schedule?season_type=REG&week=9')
        assert response.status_code == 200
        assert [g['id'] for g in response.json()['data']] == [str(ids[2]),str(ids[4]),str(ids[3])]
        assert response.json()['data'][-1]['reported_home_score'] is None
        assert http.get('/api/seasons/2026/schedule?season_type=POST').json()['data'] == []
        assert http.get('/api/seasons/2026/schedule?season_type=REG&week=1').json()['data'] == []
        assert len(http.get('/api/seasons/2025/schedule?season_type=POST&round=WC').json()['data']) == 1
        assert len(http.get('/api/seasons/2024/schedule?season_type=REG').json()['data']) == 1
        game = http.get(f'/api/games/{ids[0]}')
        assert game.status_code == 200 and game.json()['data']['reported_home_score'] == 0
        assert game.json()['data']['status'] == 'UNKNOWN'
        assert http.get(f'/api/games/{uuid4()}').status_code == 404
    assert db_session.scalar(select(func.count()).select_from(Game)) == 6


@pytest.mark.parametrize('failure,status,code', [
    (GameNotFound(),404,'GAME_NOT_FOUND'),
    (OperationalError('PRIVATE_SQL', {'password':'SYNTHETIC_PRIVATE_VALUE'}, Exception('PRIVATE_CONNECTION')),503,'DATABASE_UNAVAILABLE'),
])
def test_async_error_handler_transport(failure,status,code):
    """Handler wiring through real ASGI transport; this does not contact PostgreSQL."""
    app = application()
    async def unavailable_service():
        raise failure
    app.dependency_overrides[get_schedule_service] = unavailable_service
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as http:
            return await http.get('/api/games/00000000-0000-0000-0000-000000000001')
    response = asyncio.run(request())
    assert response.status_code == status
    assert response.json()['error']['code'] == code
    assert 'PRIVATE' not in response.text
