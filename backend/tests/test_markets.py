"""Synthetic source-reference market tests. No external fetch or development writes."""
import asyncio
import hashlib
import json
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.api.markets import get_markets_service, game_markets
from app.core.config import Settings
from app.main import create_app
from app.schemas.markets import MarketsResponse
from app.services.markets import MarketsService, reference_sides
from app.services.schedule import GameNotFound


def raw(**changes):
    return dict(away_moneyline='120',home_moneyline='-140',spread_line='3.5',
                away_spread_odds='-110',home_spread_odds='-110',total_line='44',over_odds='-110',under_odds='-110',**changes)


def result(data, away=20, home=24):
    rows, warnings = reference_sides(data,away,home)
    return {(r.market,r.side):r for r in rows},warnings


@pytest.mark.parametrize('spread,away,home,expected',[
    ('3.5',20,24,'WIN'),('3.5',21,24,'LOSS'),('3',21,24,'PUSH'),
    ('-3.5',24,20,'LOSS'),('-3.5',24,21,'WIN'),('-3',24,21,'PUSH'),('0',0,0,'PUSH'),
])
def test_signed_home_and_away_spreads(spread,away,home,expected):
    data=raw();data['spread_line']=spread
    rows,_=result(data,away,home)
    assert rows['SPREAD','HOME'].line == -Decimal(spread)
    assert rows['SPREAD','AWAY'].line == Decimal(spread)
    assert rows['SPREAD','HOME'].result==expected
    assert rows['SPREAD','AWAY'].result=={'WIN':'LOSS','LOSS':'WIN','PUSH':'PUSH'}[expected]


@pytest.mark.parametrize('total,over,under',[('43.5','WIN','LOSS'),('44.5','LOSS','WIN'),('44','PUSH','PUSH'),('44.000001','LOSS','WIN')])
def test_exact_decimal_totals(total,over,under):
    data=raw();data['total_line']=total
    rows,_=result(data)
    assert rows['TOTAL','OVER'].result==over and rows['TOTAL','UNDER'].result==under


def test_moneyline_winners_zero_scores_and_unknown_tie_rules():
    rows,_=result(raw(),0,1)
    assert rows['MONEYLINE','HOME'].result=='WIN' and rows['MONEYLINE','AWAY'].result=='LOSS'
    rows,_=result(raw(),0,0)
    assert rows['MONEYLINE','HOME'].result==rows['MONEYLINE','AWAY'].result=='UNDETERMINED'
    assert rows['MONEYLINE','HOME'].reason=='moneyline_tie_rules_unknown'


@pytest.mark.parametrize('value',['NaN','Infinity','1e5','-Infinity','not-a-number','1.1234567','99999999',True,{},[]])
def test_invalid_source_values_never_grade(value):
    data=raw();data.update(spread_line=value,total_line=value,home_moneyline=value)
    rows,_=result(data)
    assert all(rows[key].result=='UNDETERMINED' for key in [('SPREAD','HOME'),('TOTAL','OVER'),('MONEYLINE','HOME')])


def test_missing_scores_prices_and_lines_are_independent():
    data=raw();data.update(home_spread_odds='',away_moneyline='',total_line='NA')
    rows,_=result(data)
    assert rows['SPREAD','HOME'].price is None and rows['SPREAD','HOME'].result=='WIN'
    assert rows['MONEYLINE','AWAY'].result==rows['TOTAL','OVER'].result=='UNDETERMINED'
    rows,_=result(raw(),None,24)
    assert all(row.result=='UNDETERMINED' and row.reason=='scores_unavailable' for row in rows.values())


def test_zero_total_allowed_but_zero_price_and_negative_total_rejected():
    data=raw();data.update(total_line='0',home_moneyline='0')
    rows,_=result(data,0,0)
    assert rows['TOTAL','OVER'].result=='PUSH' and rows['MONEYLINE','HOME'].price is None
    data['total_line']='-1';assert result(data)[0]['TOTAL','OVER'].line is None


@pytest.fixture
def market_game(api_game):
    game=api_game
    game.source_game_id='2026_09_BUF_MIN';game.source_away_team='BUF';game.source_home_team='MIN'
    game.raw_source_record=raw()
    game.raw_source_record.update(game_id=game.source_game_id,season='2026',away_team='BUF',home_team='MIN')
    game.source_record_sha256=hashlib.sha256(json.dumps(game.raw_source_record,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    return game


def test_public_reference_provenance_and_unknown_freshness(market_game):
    repo=Mock();repo.game.return_value=market_game
    response=MarketsService(repo).game(market_game.id)
    source=response.data.references[0]
    assert source.quote_updated_at is None and source.freshness=='UNKNOWN' and source.bookmaker is None
    assert source.classification=='UNVERIFIED_SOURCE_REFERENCE' and source.origin_status=='DECLARED'
    assert source.snapshot_id==f'{market_game.source_artifact.id}:{market_game.source_record_sha256}'
    assert response.data.game.status=='UNKNOWN' and response.data.game.score_finality=='UNVERIFIED'
    assert response.meta.settlement_verified is response.meta.current_offers_available is False
    rendered=response.model_dump_json()
    for secret in ('artifact_path','raw_source_record','provenance_notes','review_token'):
        assert secret not in rendered
    assert json.loads(rendered)['data']['references'][0]['sides'][1]['line']=='3.5'
    repo.game.assert_called_once_with(market_game.id)


def test_final_evidence_does_not_verify_odds_time(market_game):
    from datetime import datetime,timezone
    market_game.status='FINAL';market_game.final_evidence_url='https://example.invalid/evidence';market_game.final_verified_at=datetime.now(timezone.utc)
    repo=Mock();repo.game.return_value=market_game
    response=MarketsService(repo).game(market_game.id)
    assert not response.meta.settlement_verified and not response.meta.verified_pregame_snapshot_available


@pytest.mark.parametrize('case',['missing','hash','identity'])
def test_unusable_source_fails_closed(market_game,case):
    if case=='missing':market_game.raw_source_record=None
    elif case=='hash':market_game.source_record_sha256='0'*64
    else:market_game.raw_source_record['home_team']='OTHER'
    repo=Mock();repo.game.return_value=market_game
    response=MarketsService(repo).game(market_game.id)
    assert response.data.references==[] and response.data.unavailable_reason


def test_missing_game_and_direct_route(market_game):
    repo=Mock();repo.game.return_value=None
    with pytest.raises(GameNotFound):MarketsService(repo).game(uuid4())
    repo.game.return_value=market_game
    service=MarketsService(repo)
    assert isinstance(game_markets(market_game.id,service),MarketsResponse)


def application():
    return create_app(Settings(db_host='synthetic.invalid',db_name='nfl_research_test',db_user='synthetic',db_password='SYNTHETIC_ONLY'))


@pytest.mark.parametrize('path,method,status',[
    ('/api/games/invalid/markets','GET',422),
    (f'/api/games/{uuid4()}/markets?apply=true','GET',422),
    (f'/api/games/{uuid4()}/markets?x=1&x=2','GET',422),
    (f'/api/games/{uuid4()}/markets','POST',405),
])
def test_http_validation_and_read_only(path,method,status):
    app=application()
    async def unused():return None
    app.dependency_overrides[get_markets_service]=unused
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            return await client.request(method,path)
    assert asyncio.run(request()).status_code==status


@pytest.mark.api
def test_http_success_missing_and_database_failure(market_game):
    from fastapi.testclient import TestClient
    app=application();repo=Mock();repo.game.return_value=market_game
    app.dependency_overrides[get_markets_service]=lambda:MarketsService(repo)
    with TestClient(app) as client:
        path=f'/api/games/{market_game.id}/markets'
        assert client.get(path).json()['data']['references'][0]['freshness']=='UNKNOWN'
        repo.game.return_value=None;assert client.get(path).status_code==404
        repo.game.side_effect=OperationalError('PRIVATE_SQL',{},Exception('PRIVATE_DETAILS'))
        response=client.get(path);assert response.status_code==503 and 'PRIVATE' not in response.text


@pytest.mark.database
def test_restricted_api_can_read_market_source_without_writes(pg_engine):
    from pydantic import SecretStr
    from app.db.session import make_engine
    from app.repositories.schedule import ScheduleRepository
    from sqlalchemy.orm import Session
    settings=Settings().model_copy(update=dict(db_user='nfl_api',db_password=SecretStr('SYNTHETIC_API_PASSWORD_123456789'),db_purpose='runtime'))
    engine=make_engine(settings)
    try:
        with engine.connect() as c,c.begin():
            c.exec_driver_sql('SET TRANSACTION READ ONLY')
            before=c.scalar(text('SELECT count(*) FROM games'))
            assert ScheduleRepository(Session(bind=c)).game(uuid4()) is None
            assert c.scalar(text('SELECT count(*) FROM games'))==before
            assert not c.scalar(text("SELECT has_table_privilege(current_user,'games','UPDATE')"))
    finally:engine.dispose()


@pytest.mark.database
def test_postgresql_populated_reference_under_api_role(db_session):
    from app.models import Game,Team,SourceArtifact
    from app.repositories.schedule import ScheduleRepository
    s=db_session
    home,away=Team(code='AAA',name='Synthetic home'),Team(code='BBB',name='Synthetic away')
    artifact=SourceArtifact(provider='nflverse',artifact_path='synthetic://market-test.csv',sha256='a'*64,byte_size=1)
    s.add_all([home,away,artifact]);s.flush()
    record=raw();record.update(game_id='2024_01_BBB_AAA',season='2024',home_team='AAA',away_team='BBB')
    digest=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    game=Game(provider='nflverse',source_game_id=record['game_id'],season=2024,season_type='REG',week=1,game_type='REG',
        home_team_id=home.id,away_team_id=away.id,source_home_team='AAA',source_away_team='BBB',
        source_artifact_id=artifact.id,source_record_sha256=digest,raw_source_record=record,
        reported_home_score=24,reported_away_score=20)
    s.add(game);s.flush();identifier=game.id
    # Same uncommitted synthetic fixture with actual restricted SQL privileges.
    s.execute(text('SET LOCAL ROLE nfl_api'))
    response=MarketsService(ScheduleRepository(s)).game(identifier)
    assert response.data.game.home_team.id==home.id
    assert response.data.references[0].sides[3].line==Decimal('-3.5')
    assert response.data.references[0].sides[3].result=='WIN'
    assert not s.new and not s.dirty and not s.deleted
    assert s.scalar(text("SELECT has_table_privilege(current_user,'games','UPDATE')")) is False
    s.execute(text('RESET ROLE'))


@pytest.mark.parametrize('captured',['2024-01-01T00:00:00+00:00','2026-11-11T22:00:00+00:00'])
def test_old_or_recent_artifact_time_never_becomes_quote_freshness(market_game,captured):
    from datetime import datetime
    market_game.source_artifact.retrieved_at=datetime.fromisoformat(captured)
    repo=Mock();repo.game.return_value=market_game
    reference=MarketsService(repo).game(market_game.id).data.references[0]
    assert reference.artifact_retrieved_at==datetime.fromisoformat(captured)
    assert reference.quote_updated_at is None and reference.freshness=='UNKNOWN'
