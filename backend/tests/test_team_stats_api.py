"""Synthetic accepted-statistics API/service/query and restricted-role regressions."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text, func
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import OperationalError, DBAPIError

from app.api.team_stats import get_team_stats_service
from app.core.config import Settings
from app.main import create_app
from app.repositories.team_stats import TeamStatsRepository, accepted_query, METRICS
from app.schemas.team_stats import GameLogFilters, SeasonFilters
from app.services.team_stats import TeamStatsService, TeamNotFound
from app.services.schedule import GameNotFound


def application():
    return create_app(Settings(db_host='synthetic.invalid', db_name='nfl_research_test',
                               db_user='synthetic', db_password='SYNTHETIC_ONLY'))


@pytest.fixture
def row():
    now=datetime(2026,11,1,tzinfo=timezone.utc)
    return dict(game_id=uuid4(),source_game_id='synthetic-game',season=2026,season_type='REG',week=9,
        scheduled_kickoff_utc=now,source_gameday=now.date(),status='UNKNOWN',
        team_id=uuid4(),team_code='AAA',team_name='Synthetic A',opponent_id=uuid4(),opponent_code='BBB',opponent_name='Synthetic B',
        side='HOME',gross_passing_yards=200,original_sack_yards=-15,net_passing_yards=185,rushing_yards=-2,
        net_passing_yards_allowed=100,rushing_yards_allowed=0,reported_points_scored=0,reported_points_allowed=None,
        accepted_pair_id=uuid4(),selection_generation=3,revision_recorded_at=now,schedule_source_artifact_id=uuid4(),
        artifact_id=uuid4(),provider='nflverse',artifact_sha256='a'*64,origin_status='DECLARED',
        documented_source_url=None,license_url=None,attribution='Synthetic',source_record_sha256='b'*64,source_line=2,
        score_finality='UNVERIFIED')


def service(row):
    repo=Mock()
    repo.team.return_value=dict(id=row['team_id'],code='AAA',name='Synthetic A')
    repo.logs.return_value=(1,[row])
    repo.game_exists.return_value=True
    return TeamStatsService(repo),repo


def test_public_projection_and_unknown_score_semantics(row):
    s,r=service(row)
    result=s.logs(row['team_id'],GameLogFilters(season=2026,season_type='REG'))
    record=result.data[0]
    assert record.net_passing_yards==185 and record.original_sack_yards==-15
    assert record.rushing_yards==-2 and record.rushing_yards_allowed==0
    assert record.status=='UNKNOWN' and record.reported_points_scored==0 and record.reported_points_allowed is None
    assert record.accepted_pair_id==row['accepted_pair_id']
    assert result.meta.total_count==1
    payload=result.model_dump_json()
    for private in ('raw_source_record','review_token','batch_id','artifact_path','provenance_notes'):
        assert private not in payload


def test_missing_team_game_and_empty_statistics(row):
    s,r=service(row);r.team.return_value=None
    with pytest.raises(TeamNotFound):s.logs(uuid4(),GameLogFilters(season=2024,season_type='REG'))
    r.game_exists.return_value=False
    with pytest.raises(GameNotFound):s.game(uuid4())
    r.game_exists.return_value=True;r.game.return_value=[]
    response=s.game(uuid4())
    assert response.data==[] and not response.meta.statistics_available
    r.game.return_value=[row]
    from sqlalchemy.exc import SQLAlchemyError
    with pytest.raises(SQLAlchemyError):s.game(row['game_id'])


def test_summary_per_metric_denominators_and_nulls(row):
    s,r=service(row)
    values={'games_with_accepted_statistics':2}
    for name in METRICS:
        values.update({name+'_total':None,name+'_average':None,name+'_count':0})
    values.update(net_passing_yards_total=285,net_passing_yards_average=142.5,net_passing_yards_count=2,
                  reported_points_scored_total=0,reported_points_scored_average=0,reported_points_scored_count=1)
    r.summary.return_value=values
    data=s.summary(row['team_id'],SeasonFilters(season=2026,season_type='REG')).data
    assert data.net_passing_yards.average==142.5
    assert data.reported_points_scored.games_with_values==1 and data.reported_points_scored.total==0
    assert data.verified_final_points_scored.total is None
    assert data.rushing_yards.average is None


def test_queries_select_only_allowed_columns_and_single_snapshot_page(row):
    sql=str(accepted_query().compile(dialect=dialect()))
    assert 'team_stats_accepted.pair_id' in sql and 'team_stats_pairs.id = team_stats_accepted.pair_id' in sql
    assert sql.count('JOIN team_game_stat_revisions AS')==2
    for forbidden in ('raw_source_record','review_token','team_stats_batches','team_stats_selection_events','content_sha256'):
        assert forbidden not in sql
    session=Mock();session.execute.return_value.mappings.return_value.all.return_value=[dict(total_count=4,game_id=None)]
    repo=TeamStatsRepository(session)
    assert repo.logs(uuid4(),GameLogFilters(season=2025,season_type='POST',week=19,limit=1,offset=10))==(4,[])
    compiled=session.execute.call_args.args[0].compile(dialect=dialect())
    assert 'LEFT OUTER JOIN page ON true' in str(compiled)
    assert 'NULLS LAST' in str(compiled) and 'LIMIT' in str(compiled) and 'OFFSET' in str(compiled)
    assert 2025 in compiled.params.values() and 'POST' in compiled.params.values() and 19 in compiled.params.values()
    session.execute.assert_called_once()
    repo.summary(uuid4(),SeasonFilters(season=2024,season_type='REG'))
    summary_sql=str(session.execute.call_args.args[0].compile(dialect=dialect()))
    assert 'avg(' in summary_sql and 'count(accepted_stats.net_passing_yards)' in summary_sql


@pytest.mark.parametrize('query',[
    '', 'season=2023&season_type=REG','season=2027&season_type=REG','season=2024&season_type=ALL',
    'season=2024&season_type=REG&week=19','season=2024&season_type=POST&week=18',
    'season=2024&season_type=REG&limit=0','season=2024&season_type=REG&limit=101',
    'season=2024&season_type=REG&offset=-1','season=2024&season_type=REG&week=1&week=2',
    'season=2024&season_type=REG&private=PRIVATE_VALUE'])
def test_http_invalid_filters(query):
    app=application()
    async def unused():return None
    app.dependency_overrides[get_team_stats_service]=unused
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            return await client.get(f'/api/teams/{uuid4()}/games?'+query)
    response=asyncio.run(request())
    assert response.status_code==422 and 'PRIVATE_VALUE' not in response.text


@pytest.mark.parametrize('method',['POST','PUT','PATCH','DELETE'])
def test_read_only_methods(method):
    async def request():
        async with AsyncClient(transport=ASGITransport(app=application()),base_url='http://test') as client:
            return await client.request(method,f'/api/games/{uuid4()}/team-stats')
    assert asyncio.run(request()).status_code==405


@pytest.mark.api
def test_http_success_and_errors(row):
    s,r=service(row);app=application();app.dependency_overrides[get_team_stats_service]=lambda:s
    with TestClient(app) as client:
        path=f'/api/teams/{row["team_id"]}/games?season=2026&season_type=REG'
        response=client.get(path)
        assert response.status_code==200 and set(response.json())=={'data','meta'}
        away=dict(row,side='AWAY',team_id=row['opponent_id'],team_code='BBB',team_name='Synthetic B',
                  opponent_id=row['team_id'],opponent_code='AAA',opponent_name='Synthetic A')
        r.game.return_value=[row,away]
        game_response=client.get(f'/api/games/{row["game_id"]}/team-stats')
        assert game_response.status_code==200
        assert [x['side'] for x in game_response.json()['data']]==['HOME','AWAY']
        assert all(x['status']=='UNKNOWN' for x in game_response.json()['data'])
        r.game.return_value=[]
        assert client.get(f'/api/games/{row["game_id"]}/team-stats').json()['meta']['statistics_available'] is False
        r.summary.return_value=dict(games_with_accepted_statistics=0,
            **{name+suffix:value for name in METRICS for suffix,value in (('_total',None),('_average',None),('_count',0))})
        summary=client.get(f'/api/teams/{row["team_id"]}/stats?season=2026&season_type=POST')
        assert summary.status_code==200 and summary.json()['data']['net_passing_yards']['total'] is None
        r.logs.return_value=(0,[])
        assert client.get(path).json()['data']==[]
        r.team.return_value=None
        assert client.get(path).json()['error']['code']=='TEAM_NOT_FOUND'
        r.team.side_effect=OperationalError('PRIVATE',{},Exception('PRIVATE'))
        response=client.get(path)
        assert response.status_code==503 and 'PRIVATE' not in response.text


@pytest.mark.database
def test_actual_api_login_column_grants_and_denials(pg_engine):
    from pydantic import SecretStr
    from app.db.session import make_engine
    from app.db.roles import API_STATS_COLUMNS, grant_api_stats
    # Grants are idempotent; only the isolated test database is touched by the fixture.
    with pg_engine.begin() as c:
        grant_api_stats(c);grant_api_stats(c)
    settings=Settings().model_copy(update=dict(db_user='nfl_api',db_password=SecretStr('SYNTHETIC_API_PASSWORD_123456789'),db_purpose='runtime'))
    engine=make_engine(settings)
    try:
        with engine.connect() as c, c.begin():
            assert c.scalar(text('SELECT session_user'))=='nfl_api'
            c.execute(accepted_query()).all()
            for table,columns in API_STATS_COLUMNS.items():
                c.exec_driver_sql(f"SELECT {', '.join(columns)} FROM {table}").all()
            for statement in ('SELECT raw_source_record FROM team_game_stat_revisions',
                "INSERT INTO team_stats_batches(id,kind,candidate_sha256,review_token,evidence) VALUES(gen_random_uuid(),'IMPORT',repeat('a',64),repeat('b',64),'{}')",
                'SELECT review_token FROM team_stats_batches',
                'SELECT batch_id FROM team_stats_pairs','SELECT batch_id FROM team_stats_accepted',
                'SELECT * FROM team_stats_batches','SELECT * FROM team_stats_selection_events',
                'UPDATE team_stats_accepted SET generation=generation+1','DELETE FROM team_stats_pairs',
                'TRUNCATE team_stats_selection_events','ALTER TABLE team_stats_accepted DISABLE TRIGGER ALL',
                'SET ROLE nfl_owner','CREATE TABLE public.forbidden(id int)'):
                with pytest.raises(DBAPIError) as exc:
                    with c.begin_nested():c.exec_driver_sql(statement)
                assert exc.value.orig.sqlstate=='42501'
    finally:engine.dispose()


@pytest.mark.database
def test_accepted_selection_opponent_aggregation_filters_and_corrections(db_candidate,tmp_path):
    # Existing synthetic full-contract fixture; no real artifacts are imported.
    from test_team_stats_ingestion import approved_import, make_files
    from ingestion.team_stats.candidate import load_candidate, archive_candidate
    from ingestion.team_stats.storage import inspect,plan_import,apply_import,plan_rollback,apply_rollback
    from app.models import Game,TeamStatsAccepted
    session,candidate,archives,files,rows,identities=db_candidate
    approved_import(db_candidate)
    game=session.scalar(select(Game).where(Game.season==2024,Game.season_type=='REG',Game.week==2).order_by(Game.source_game_id))
    team=game.home_team_id
    repo=TeamStatsRepository(session)
    filters=GameLogFilters(season=2024,season_type='REG',limit=1)
    total,page=repo.logs(team,filters)
    assert total>1 and len(page)==1
    assert repo.logs(team,filters.model_copy(update={'offset':10000}))==(total,[])
    stage=repo.logs(team,GameLogFilters(season=2024,season_type='POST'))[1]
    assert all(r['season_type']=='POST' for r in stage)
    assert all(r['week']==1 for r in repo.logs(team,GameLogFilters(season=2024,season_type='REG',week=1))[1])
    pair=repo.game(game.id)
    assert [r['side'] for r in pair]==['HOME','AWAY']
    assert pair[0]['net_passing_yards']==190 and pair[0]['net_passing_yards_allowed']==190
    assert pair[0]['opponent_id']==pair[1]['team_id']
    assert all(r['score_finality']!='CONFIRMED_FINAL' for r in pair)
    summary=repo.summary(team,filters)
    assert int(summary['net_passing_yards_total'])==190*total
    assert summary['verified_final_points_scored_count']==0
    old_pair=pair[0]['accepted_pair_id']
    source_id=game.source_game_id
    def correction(year,records):
        for record in records:
            if year==2024 and record['game_id']==source_id:record['rushing_yards']='-3'
    changed=load_candidate(**make_files(tmp_path/'correction',rows,identities,correction))
    captures=archive_candidate(changed,tmp_path/'archives')
    plan=plan_import(inspect(session),changed)
    applied=apply_import(session,changed,captures,plan['review_token'])
    assert repo.game(game.id)[0]['rushing_yards']==-3
    rollback=plan_rollback(session,inspect(session),applied['batch_id'])
    apply_rollback(session,applied['batch_id'],rollback['review_token'])
    assert repo.game(game.id)[0]['accepted_pair_id']==old_pair
    assert repo.game(game.id)[0]['rushing_yards']==0
    # A complete but never-accepted revision must also stay invisible.
    from app.models import TeamStatsBatch,TeamStatsPair,TeamGameStatRevision
    old=session.get(TeamStatsPair,old_pair)
    batch=TeamStatsBatch(kind='IMPORT',candidate_sha256='d'*64,review_token='e'*64,evidence={})
    session.add(batch);session.flush()
    never=TeamStatsPair(game_id=game.id,home_team_id=game.home_team_id,away_team_id=game.away_team_id,
        batch_id=batch.id,source_artifact_id=old.source_artifact_id,previous_pair_id=old.id,
        definition_version=old.definition_version,content_sha256='f'*64)
    session.add(never);session.flush()
    for original in session.scalars(select(TeamGameStatRevision).where(TeamGameStatRevision.pair_id==old.id)):
        fields={column.name:getattr(original,column.name) for column in original.__table__.columns}
        fields.update(pair_id=never.id,rushing_yards=999)
        session.add(TeamGameStatRevision(**fields))
    session.flush()
    assert repo.game(game.id)[0]['accepted_pair_id']==old_pair
    assert repo.game(game.id)[0]['rushing_yards']==0
    game.reported_home_score=None;game.reported_away_score=None;session.flush()
    assert repo.game(game.id)[0]['reported_points_scored'] is None
    assert repo.game(game.id)[0]['score_finality']=='NOT_REPORTED'
    missing_scores=repo.summary(team,SeasonFilters(season=2026,season_type='REG'))
    assert missing_scores['reported_points_scored_count']==0 and missing_scores['reported_points_scored_total'] is None
    assert repo.logs(team,GameLogFilters(season=2026,season_type='POST'))==(0,[])
    game.scheduled_kickoff_utc=None
    game.reported_home_score=0;game.reported_away_score=7
    game.status='FINAL';game.final_evidence_url='https://example.invalid/synthetic-independent-final-evidence'
    game.final_verified_at=datetime(2026,11,1,tzinfo=timezone.utc)
    session.flush()
    assert repo.game(game.id)[0]['score_finality']=='CONFIRMED_FINAL'
    assert repo.summary(team,filters)['verified_final_points_scored_count']==1
    ordered=repo.logs(team,filters.model_copy(update={'limit':100}))[1]
    assert ordered[-1]['game_id']==game.id and ordered[-1]['scheduled_kickoff_utc'] is None
    assert all(row['season']==2025 for row in repo.logs(team,GameLogFilters(season=2025,season_type='REG'))[1])
    # Run the populated query using restricted SQL privileges in the same uncommitted fixture.
    session.execute(text('SET LOCAL ROLE nfl_api'))
    assert repo.logs(team,filters)[0]==total
    assert repo.summary(team,filters)['net_passing_yards_count']==total
    session.execute(text('RESET ROLE'))


# Reuse synthetic ingestion fixture without collecting imported tests.
from test_team_stats_ingestion import db_candidate
from test_ingestion import source_rows


@pytest.mark.parametrize('path',[
    '/api/games/not-a-uuid/team-stats',
    '/api/games/00000000-0000-0000-0000-000000000001/team-stats?secret=PRIVATE_VALUE',
    '/api/teams/not-a-uuid/stats?season=2024&season_type=REG',
    '/api/teams/00000000-0000-0000-0000-000000000001/stats?season=2026&season_type=REG&week=1',
    '/api/teams/00000000-0000-0000-0000-000000000001/stats?season=2026&season_type=POST&season_type=REG',
])
def test_other_endpoint_validation(path):
    app=application()
    async def unused():return None
    app.dependency_overrides[get_team_stats_service]=unused
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as c:
            return await c.get(path)
    response=asyncio.run(request())
    assert response.status_code==422 and 'PRIVATE_VALUE' not in response.text


@pytest.mark.parametrize('failure,code,status',[
    (TeamNotFound(),'TEAM_NOT_FOUND',404),
    (GameNotFound(),'GAME_NOT_FOUND',404),
    (OperationalError('PRIVATE',{},Exception('PRIVATE')),'DATABASE_UNAVAILABLE',503),
])
def test_async_error_transport(failure,code,status):
    app=application()
    async def fail():raise failure
    app.dependency_overrides[get_team_stats_service]=fail
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as c:
            return await c.get(f'/api/games/{uuid4()}/team-stats')
    response=asyncio.run(request())
    assert response.status_code==status and response.json()['error']['code']==code
    assert 'PRIVATE' not in response.text


def test_openapi_public_response_contracts():
    schema=application().openapi()
    for path in ('/api/teams/{team_id}/games','/api/games/{game_id}/team-stats','/api/teams/{team_id}/stats'):
        assert set(schema['paths'][path])=={'get'}
        assert '422' in schema['paths'][path]['get']['responses']
    assert 'raw_source_record' not in str(schema)
    sql=str(accepted_query().compile(dialect=dialect()))
    assert 'games.final_evidence_url IS NOT NULL' in sql
    assert 'games.final_verified_at IS NOT NULL' in sql
