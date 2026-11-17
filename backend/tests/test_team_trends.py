"""Synthetic recent-trend SQL execution and HTTP tests, without external services.

SQLite uses only a minimal projection of existing tables, not application DDL or
migrations. PostgreSQL-only permission/trigger behavior has a separate marked test.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import Column, MetaData, Table, create_engine, event, select, text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.team_stats import get_team_stats_service, team_trends
from app.core.config import Settings
from app.db.roles import API_STATS_COLUMNS
from app.main import create_app
from app.models import Game, SourceArtifact, Team, TeamStatsAccepted, TeamStatsPair, TeamGameStatRevision
from app.repositories.team_stats import TeamStatsRepository, trends_query
from app.schemas.team_stats import TrendFilters, TeamTrendsResponse
from app.services.team_stats import TeamStatsService, InvalidTrendMatchup, TeamNotFound
from app.services.schedule import GameNotFound


@pytest.fixture
def dataset():
    metadata = MetaData()
    columns = {
        Team: ('id', 'code', 'name'),
        SourceArtifact: ('id', 'provider', 'sha256', 'origin_status', 'documented_source_url', 'license_url', 'attribution'),
        Game: ('id', 'provider', 'source_game_id', 'season', 'season_type', 'week', 'scheduled_kickoff_utc',
               'source_gameday', 'source_artifact_id', 'reported_home_score', 'reported_away_score', 'status',
               'final_evidence_url', 'final_verified_at', 'home_team_id', 'away_team_id'),
        TeamStatsAccepted: API_STATS_COLUMNS['team_stats_accepted'],
        TeamStatsPair: API_STATS_COLUMNS['team_stats_pairs'],
        TeamGameStatRevision: API_STATS_COLUMNS['team_game_stat_revisions'],
    }
    tables = {model: Table(model.__tablename__, metadata,
        *[Column(name, model.__table__.c[name].type, primary_key=model.__table__.c[name].primary_key)
          for name in names]) for model, names in columns.items()}
    engine = create_engine('sqlite://')
    metadata.create_all(engine)
    with Session(engine) as session:
        team, opponent, stranger, artifact = uuid4(), uuid4(), uuid4(), uuid4()
        session.execute(tables[Team].insert(), [dict(id=team, code='AAA', name='Synthetic A'),
            dict(id=opponent, code='BBB', name='Synthetic B'), dict(id=stranger, code='CCC', name='Synthetic C')])
        session.execute(tables[SourceArtifact].insert(), dict(id=artifact, provider='nflverse', sha256='a'*64,
            origin_status='DECLARED', attribution='Synthetic fixture', documented_source_url=None, license_url=None))
        start = datetime(2026, 9, 1, tzinfo=timezone.utc)

        def add(index, *, season=2026, stage='REG', dated=True, accepted=True, reciprocal=True,
                own=None, other=None, scores=(None, None), kickoff=None, home=True, provider='nflverse'):
            game_id, pair_id = uuid4(), uuid4()
            date = (kickoff or start+timedelta(days=index*7)) if dated else None
            session.execute(tables[Game].insert(), dict(id=game_id, provider=provider,
                source_game_id=f'synthetic-{season}-{stage}-{index:02}', season=season, season_type=stage,
                week=index, scheduled_kickoff_utc=date, source_gameday=date.date() if date else None,
                source_artifact_id=artifact, reported_home_score=scores[0], reported_away_score=scores[1],
                home_team_id=team if home else opponent, away_team_id=opponent if home else team,
                status='UNKNOWN', final_evidence_url=None, final_verified_at=None))
            session.execute(tables[TeamStatsPair].insert(), dict(id=pair_id, game_id=game_id,
                source_artifact_id=artifact, definition_version='net_pass_negative_sacks_v1', recorded_at=start))
            for identity, other_id, side, metric in ((team, opponent, 'HOME' if home else 'AWAY', own),
                                                    (opponent, team, 'AWAY' if home else 'HOME', other)):
                if identity == opponent and not reciprocal:
                    continue
                metric = dict(net_passing_yards=100*index, rushing_yards=10*index) if metric is None else metric
                net = metric.get('net_passing_yards')
                session.execute(tables[TeamGameStatRevision].insert(), dict(pair_id=pair_id, game_id=game_id,
                    team_id=identity, opponent_team_id=other_id, side=side,
                    gross_passing_yards=net+10 if net is not None else None, original_sack_yards=-10,
                    net_passing_yards=net, rushing_yards=metric.get('rushing_yards'),
                    source_record_sha256='b'*64, source_line=2))
            if accepted:
                session.execute(tables[TeamStatsAccepted].insert(), dict(game_id=game_id, pair_id=pair_id, generation=1))
            return game_id, pair_id

        yield session, tables, team, opponent, stranger, add
    engine.dispose()


def trends(dataset, **changes):
    session, _, team, *_ = dataset
    return TeamStatsService(TeamStatsRepository(session)).trends(team,
        TrendFilters(season=changes.pop('season', 2026), season_type=changes.pop('season_type', 'REG'), **changes))


@pytest.mark.parametrize('window,size', [('L3',3), ('L5',5), ('L10',10)])
def test_real_sql_selects_latest_window_and_all_six_averages(dataset, window, size):
    *_, add = dataset
    # Reverse insertion order and alternating sides catch ID/order/home-score mistakes.
    ids = {i: add(i, own=dict(net_passing_yards=i*100, rushing_yards=i*10),
        other=dict(net_passing_yards=i*50, rushing_yards=i*5), scores=(i*3,i*2), home=i%2==0)[0]
        for i in reversed(range(1,13))}
    result = trends(dataset, window=window)
    selected = list(range(12,12-size,-1))
    data = result.data
    assert [g.game_id for g in data.games] == [ids[i] for i in selected]
    assert data.eligible_game_count == size and data.requested_game_count == size
    avg = sum(selected)/size
    assert data.offense.net_passing_yards.average == 100*avg  # NET, not gross (+10)
    assert data.offense.rushing_yards.average == 10*avg
    assert data.defense.net_passing_yards_allowed.average == 50*avg
    assert data.defense.rushing_yards_allowed.average == 5*avg
    assert data.offense.reported_points_scored.average == sum(i*(3 if i%2==0 else 2) for i in selected)/size
    assert data.defense.reported_points_allowed.average == sum(i*(2 if i%2==0 else 3) for i in selected)/size
    assert result.meta.available_eligible_games == 12
    assert result.meta.window_complete and result.meta.selected_metrics_complete
    assert result.meta.selected_unknown_status_games == size
    assert result.meta.selected_unverified_score_games == size
    assert not result.meta.completion_before_cutoff_verified


@pytest.mark.parametrize('window', ['L3','L5','L10'])
@pytest.mark.parametrize('available', [0,1,2])
def test_small_empty_samples_and_no_zero_filling(dataset, window, available):
    *_, add = dataset
    for i in range(1,available+1):
        add(i, own=dict(net_passing_yards=0, rushing_yards=-2))
    result = trends(dataset, window=window)
    assert result.data.eligible_game_count == available
    assert result.data.offense.net_passing_yards.average == (0 if available else None)
    assert result.data.offense.rushing_yards.average == (-2 if available else None)
    assert result.data.offense.reported_points_scored.average is None
    assert result.meta.missing_metric_games['reported_points_scored'] == available
    assert not result.meta.window_complete and not result.meta.selected_metrics_complete


def test_missing_metrics_do_not_backfill_older_games(dataset):
    *_, add = dataset
    add(1)
    add(2, own=dict(net_passing_yards=None, rushing_yards=0), scores=(0,7))
    add(3, own=dict(net_passing_yards=-5, rushing_yards=None))
    add(4, own=dict(net_passing_yards=15, rushing_yards=4))
    result = trends(dataset, window='L3')
    assert result.data.offense.net_passing_yards.total == 10
    assert result.data.offense.net_passing_yards.average == 5
    assert result.data.offense.net_passing_yards.games_with_values == 2
    assert result.data.offense.rushing_yards.average == 2
    assert result.data.offense.reported_points_scored.average == 0
    assert result.data.offense.reported_points_scored.games_with_values == 1
    assert result.meta.window_complete and not result.meta.selected_metrics_complete


@pytest.mark.parametrize('season', [2024,2025,2026])
@pytest.mark.parametrize('stage', ['REG','POST'])
def test_season_and_stage_are_separate(dataset, season, stage):
    *_, add = dataset
    for year in (2024,2025,2026):
        for kind in ('REG','POST'):
            add(1, season=year, stage=kind)
    result = trends(dataset, season=season, season_type=stage)
    assert result.data.eligible_game_count == 1
    assert all(g.season==season and g.season_type==stage for g in result.data.games)
    assert result.meta.accepted_games_in_season_stage == 1


def test_accepted_reciprocal_eligibility_unknown_dates_and_schedule_gaps(dataset):
    *_, add = dataset
    expected, _ = add(1)
    add(2, accepted=False)  # Complete but never accepted.
    add(3, reciprocal=False)  # Unexpected damaged pair must not contribute.
    add(4, dated=False)
    add(5, provider='unapproved')
    result = trends(dataset)
    assert [g.game_id for g in result.data.games] == [expected]
    assert result.meta.accepted_games_in_season_stage == 2
    assert result.meta.excluded_unknown_kickoff_games == 1
    assert result.meta.scheduled_games_in_scope == 3
    assert result.meta.scheduled_games_without_accepted_statistics == 2


@pytest.mark.parametrize('upcoming', [False,True])
def test_matchup_excludes_itself_same_time_and_later_games(dataset, upcoming):
    session, tables, _, _, _, add = dataset
    earlier = [add(i)[0] for i in range(1,6)]
    # Both an unaccepted future matchup and an accepted historical matchup use the same bound.
    kickoff = datetime(2030 if upcoming else 2026,11,1,tzinfo=timezone.utc)
    anchor, _ = add(6, accepted=not upcoming, kickoff=kickoff)
    add(7, kickoff=kickoff)  # Equal kickoff must also be excluded.
    add(8, kickoff=kickoff+timedelta(days=1))
    add(9, dated=False)
    result = trends(dataset, window='L3', matchup_id=anchor)
    assert [g.game_id for g in result.data.games] == list(reversed(earlier[-3:]))
    assert result.meta.selection_mode == 'before_matchup'
    assert result.meta.available_eligible_games == 5
    assert result.meta.excluded_at_or_after_matchup_games == (2 if upcoming else 3)
    assert result.meta.excluded_unknown_kickoff_games == 1
    assert all(g.status=='UNKNOWN' for g in result.data.games)
    # Read-only queries did not promote the selected matchup based on scores/date.
    assert session.scalar(select(tables[Game].c.status).where(tables[Game].c.id==anchor)) == 'UNKNOWN'


def test_unknown_matchup_kickoff_never_falls_back_to_latest(dataset):
    *_, add = dataset
    add(1)
    matchup, _ = add(2, dated=False)
    result = trends(dataset, matchup_id=matchup)
    assert result.data.eligible_game_count == 0 and result.data.games == []
    assert result.data.offense.net_passing_yards.average is None
    assert result.meta.unavailable_reason == 'matchup_kickoff_unknown'
    assert result.meta.cutoff_utc is None


def test_first_matchup_has_no_history_and_unknown_team_game_context(dataset):
    session, tables, team, _, stranger, add = dataset
    first, _ = add(1)
    assert trends(dataset, matchup_id=first).data.eligible_game_count == 0
    with pytest.raises(GameNotFound): trends(dataset, matchup_id=uuid4())
    with pytest.raises(InvalidTrendMatchup): trends(dataset, season=2025, matchup_id=first)
    with pytest.raises(InvalidTrendMatchup): trends(dataset, season_type='POST', matchup_id=first)
    service = TeamStatsService(TeamStatsRepository(session))
    with pytest.raises(InvalidTrendMatchup):
        service.trends(stranger, TrendFilters(season=2026,season_type='REG',matchup_id=first))
    with pytest.raises(TeamNotFound):
        service.trends(uuid4(), TrendFilters(season=2026,season_type='REG'))


def test_tied_kickoffs_have_stable_source_id_order(dataset):
    *_, add = dataset
    when = datetime(2026,10,1,tzinfo=timezone.utc)
    ids = {i:add(i, kickoff=when)[0] for i in (2,4,1,3)}
    assert [g.game_id for g in trends(dataset,window='L3').data.games] == [ids[4],ids[3],ids[2]]


def test_only_current_accepted_revision_and_its_reciprocal_opponent_contribute(dataset):
    session, tables, team, opponent, _, add=dataset
    game_id, original_pair=add(1)
    original=trends(dataset).data
    assert original.offense.net_passing_yards.average==100
    pair_id=uuid4()
    pair=dict(session.execute(select(tables[TeamStatsPair]).where(
        tables[TeamStatsPair].c.id==original_pair)).mappings().one())
    pair['id']=pair_id
    session.execute(tables[TeamStatsPair].insert(),pair)
    for row in session.execute(select(tables[TeamGameStatRevision]).where(
            tables[TeamGameStatRevision].c.pair_id==original_pair)).mappings().all():
        changed=dict(row,pair_id=pair_id)
        changed['net_passing_yards']=300 if row['team_id']==team else 450
        changed['gross_passing_yards']=changed['net_passing_yards']+10
        session.execute(tables[TeamGameStatRevision].insert(),changed)
    assert trends(dataset).data.offense.net_passing_yards.average==100  # Never accepted yet.
    session.execute(tables[TeamStatsAccepted].update().where(tables[TeamStatsAccepted].c.game_id==game_id)
        .values(pair_id=pair_id,generation=2))
    current=trends(dataset).data
    assert current.eligible_game_count==1
    assert current.offense.net_passing_yards.average==300
    assert current.defense.net_passing_yards_allowed.average==450
    assert current.games[0].accepted_pair_id==pair_id and current.games[0].selection_generation==2
    # Logical rollback changes the pointer, without deleting or summing both revisions.
    session.execute(tables[TeamStatsAccepted].update().where(tables[TeamStatsAccepted].c.game_id==game_id)
        .values(pair_id=original_pair,generation=3))
    assert trends(dataset).data.offense.net_passing_yards.average==100


def test_final_evidence_remains_distinct_from_reported_points(dataset):
    session,tables,_,_,_,add=dataset
    add(1,scores=(0,7))
    game_id,_=add(2,scores=(14,10))
    session.execute(tables[Game].update().where(tables[Game].c.id==game_id).values(
        status='FINAL',final_evidence_url='https://example.invalid/synthetic-final',
        final_verified_at=datetime(2026,11,1,tzinfo=timezone.utc)))
    result=trends(dataset)
    assert result.data.offense.reported_points_scored.average==7
    assert result.meta.selected_unknown_status_games==1
    assert result.meta.selected_unverified_score_games==1
    assert result.data.games[0].score_finality=='CONFIRMED_FINAL'
    assert not result.meta.completion_before_cutoff_verified


def test_query_is_bounded_single_snapshot_and_allowed_projection(dataset):
    session, _, team, *_ = dataset
    statements = []
    def capture(connection, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(session.bind, 'before_cursor_execute', capture)
    try:
        trends(dataset)
    finally:
        event.remove(session.bind, 'before_cursor_execute', capture)
    assert len(statements)==2  # Identity + one statement for context/selection/aggregates/coverage.
    query=trends_query(team,TrendFilters(season=2026,season_type='POST',window='L10',matchup_id=uuid4()))
    compiled=query.compile(dialect=dialect())
    sql=str(compiled)
    assert 'LIMIT' in sql and 10 in compiled.params.values()
    assert 'POST' in compiled.params.values() and 2026 in compiled.params.values()
    assert 'team_stats_pairs.id = team_stats_accepted.pair_id' in sql
    assert sql.count('JOIN team_game_stat_revisions AS')==2
    assert 'recent_games AS' in sql and 'avg(recent_games.net_passing_yards)' in sql
    for private in ('raw_source_record','batch_id','review_token','content_sha256','team_stats_selection_events'):
        assert private not in sql


async def request(app, path, method='GET'):
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        return await client.request(method,path)


def application(service=None):
    app=create_app(Settings(db_host='synthetic.invalid',db_name='nfl_research_test',
                            db_user='synthetic',db_password='SYNTHETIC_ONLY'))
    async def dependency(): return service
    app.dependency_overrides[get_team_stats_service]=dependency
    return app


def test_response_schema_and_direct_route(dataset):
    session, _, team, _, _, add=dataset
    add(1,scores=(0,7))
    service=TeamStatsService(TeamStatsRepository(session))
    result=team_trends(team,TrendFilters(season=2026,season_type='REG'),service)
    parsed=TeamTrendsResponse.model_validate_json(result.model_dump_json())
    assert parsed.data.offense.reported_points_scored.average==0
    assert parsed.data.games[0].status=='UNKNOWN'
    assert parsed.data.window=='L5'
    for private in ('raw_source_record','review_token','batch_id','artifact_path'):
        assert private not in result.model_dump_json()


@pytest.mark.api
def test_success_http(dataset):
    session, _, team, _, _, add=dataset
    add(1,scores=(0,7))
    result=trends(dataset)
    # Precomputed synthetic response avoids sharing a SQLite connection across worker threads.
    class Facade:
        def trends(self, team_id, filters):
            assert team_id==team and filters.window=='L5'
            return result
    with TestClient(application(Facade())) as client:
        response=client.get(f'/api/teams/{team}/trends?season=2026&season_type=REG')
    assert response.status_code==200
    parsed=TeamTrendsResponse.model_validate(response.json())
    assert parsed.data.offense.reported_points_scored.average==0
    assert parsed.data.games[0].status=='UNKNOWN'
    assert parsed.data.window=='L5'
    for private in ('raw_source_record','review_token','batch_id','artifact_path'):
        assert private not in response.text


@pytest.mark.parametrize('query', ['', 'season=2023&season_type=REG', 'season=2027&season_type=REG',
    'season=2026', 'season=2026&season_type=COMBINED', 'season=2026&season_type=REG&window=3',
    'season=2026&season_type=REG&window=L4', 'season=2026&season_type=REG&window=L3&window=L5',
    'season=2026&season_type=REG&season=2025', 'season=2026&season_type=REG&matchup_id=bad',
    'season=2026&season_type=REG&cutoff=PRIVATE_VALUE'])
def test_invalid_http_filters(query):
    response=asyncio.run(request(application(),f'/api/teams/{uuid4()}/trends?'+query))
    assert response.status_code==422 and response.json()['error']['code']=='VALIDATION_ERROR'
    assert 'PRIVATE_VALUE' not in response.text


def test_invalid_team_uuid():
    response=asyncio.run(request(application(),'/api/teams/not-a-uuid/trends?season=2026&season_type=REG'))
    assert response.status_code==422


@pytest.mark.parametrize('failure,status,code', [(TeamNotFound(),404,'TEAM_NOT_FOUND'),
    (GameNotFound(),404,'GAME_NOT_FOUND'), (InvalidTrendMatchup(),422,'VALIDATION_ERROR'),
    (OperationalError('PRIVATE',{},Exception('PRIVATE')),503,'DATABASE_UNAVAILABLE')])
def test_error_transport(failure,status,code):
    async def fail(): raise failure
    app=application()
    app.dependency_overrides[get_team_stats_service]=fail
    response=asyncio.run(request(app,f'/api/teams/{uuid4()}/trends?season=2026&season_type=REG'))
    assert response.status_code==status and response.json()['error']['code']==code
    assert 'PRIVATE' not in response.text


@pytest.mark.parametrize('method',['POST','PUT','PATCH','DELETE'])
def test_read_only_and_openapi(method):
    app=application()
    response=asyncio.run(request(app,f'/api/teams/{uuid4()}/trends',method))
    assert response.status_code==405
    route=app.openapi()['paths']['/api/teams/{team_id}/trends']
    assert set(route)=={'get'}
    assert route['get']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('TeamTrendsResponse')


@pytest.mark.database
def test_postgresql_api_role_can_execute_trends(pg_engine):
    """Owner-run isolated PostgreSQL query execution under existing column grants."""
    from pydantic import SecretStr
    from app.db.session import make_engine
    settings=Settings().model_copy(update=dict(db_user='nfl_api',
        db_password=SecretStr('SYNTHETIC_API_PASSWORD_123456789'),db_purpose='runtime'))
    engine=make_engine(settings)
    try:
        with engine.connect() as connection,connection.begin():
            assert connection.scalar(text('SELECT session_user'))=='nfl_api'
            for window in ('L3','L5','L10'):
                for stage in ('REG','POST'):
                    row=connection.execute(trends_query(uuid4(),TrendFilters(season=2026,
                        season_type=stage,window=window,matchup_id=uuid4()))).mappings().one()
                    assert row['selected_count']==0 and row['game_id'] is None
    finally:
        engine.dispose()
