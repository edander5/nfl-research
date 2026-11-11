"""Synthetic exact ranking, HTTP contracts and isolated restricted-role query tests."""
import asyncio
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import OperationalError, DBAPIError

from app.api.team_rankings import get_team_rankings_service
from app.core.config import Settings
from app.main import create_app
from app.repositories.team_rankings import CATEGORIES, TeamRankingsRepository, league_query
from app.schemas.team_rankings import RankingFilters
from app.services.team_rankings import rank_category, TeamRankingsService
from app.services.team_stats import TeamNotFound


def row(code, passing, rushing=None, count=1, scheduled=None):
    result=dict(team_id=uuid4(),code=code,name='Synthetic '+code,accepted_count=count,
                scheduled_games=count if scheduled is None else scheduled,unknown_count=count,unverified_count=count)
    for category in CATEGORIES:
        result[category+'_count']=count
        result[category+'_total']=passing if category.startswith('passing') else (passing if rushing is None else rushing)
    return result


def rankings(rows,**filters):
    repository=Mock();repository.league.return_value=rows
    return TeamRankingsService(repository).rankings(RankingFilters(season=2026,**filters))


def application():
    return create_app(Settings(db_host='synthetic.invalid',db_name='nfl_research_test',
        db_user='synthetic',db_password='SYNTHETIC_ONLY'))


def test_offense_defense_direction_ties_and_stable_secondary_sort():
    rows=[row('DDD',50),row('CCC',100),row('AAA',200),row('BBB',100)]
    response=rankings(rows)
    passing=response.data[0]
    assert [t.team.code for t in passing.teams]==['AAA','BBB','CCC','DDD']
    assert [t.rank for t in passing.teams]==[1,2,2,4]
    defense=response.data[2]
    assert [t.team.code for t in defense.teams]==['DDD','BBB','CCC','AAA']
    assert [t.rank for t in defense.teams]==[1,2,2,4]
    assert passing.direction=='descending' and defense.direction=='ascending'
    assert response.meta.unknown_status_accepted_games==2


def test_exact_ratios_rank_without_rounding_and_true_ratio_ties():
    a=row('AAA',1,count=3);b=row('BBB',2,count=6);c=row('CCC',333333334,count=1000000000)
    teams=rank_category([b,a,c],'passing_offense').teams
    assert [(t.team.code,t.rank) for t in teams]==[('CCC',1),('AAA',2),('BBB',2)]
    # Float averages cannot distinguish these, but exact fractions must rank correctly.
    teams=rank_category([row('AAA',10**18),row('BBB',10**18+1)],'passing_offense').teams
    assert [t.team.code for t in teams]==['BBB','AAA'] and [t.rank for t in teams]==[1,2]


def test_category_specific_samples_null_negative_zero_and_zero_games():
    a=row('AAA',0,rushing=-3,count=1,scheduled=2)
    b=row('BBB',None,count=0,scheduled=1)
    c=row('CCC',-2,count=1)
    a['rushing_defense_count']=0;a['rushing_defense_total']=None
    result=rankings([a,b,c])
    assert result.data[0].teams[0].team.code=='AAA'
    zero=result.data[0].teams[-1]
    assert zero.team.code=='BBB' and zero.rank is None and zero.average is None
    assert zero.total_yards is None and not zero.eligible and zero.games_with_values==0
    assert result.data[3].eligible_team_count==1
    assert result.meta.missing_metric_team_games['rushing_defense']==1
    assert not result.meta.coverage_complete_for_stored_schedule


def test_team_filter_preserves_full_population_rank_and_metadata():
    a,b,c=row('AAA',300),row('BBB',200),row('CCC',100)
    result=rankings([a,b,c],category='passing_offense',team_id=c['team_id'])
    assert len(result.data)==1 and result.data[0].teams[0].rank==3
    assert result.data[0].eligible_team_count==3 and result.meta.league_team_count==3
    assert result.meta.filters.season_type=='REG'
    with pytest.raises(TeamNotFound):rankings([a,b,c],team_id=uuid4())


def test_empty_and_all_zero_game_population_has_no_ranks_or_false_completeness():
    assert not rankings([]).meta.coverage_complete_for_stored_schedule
    result=rankings([row('AAA',None,count=0,scheduled=0)],season_type='POST')
    assert all(category.eligible_team_count==0 and category.teams[0].rank is None for category in result.data)
    assert not result.meta.coverage_complete_for_stored_schedule


def test_all_32_teams_are_retained_even_when_some_metrics_or_games_are_absent():
    rows=[row(f'T{i:02}',i if i else None,count=int(i>0),scheduled=1) for i in range(32)]
    result=rankings(rows)
    assert result.meta.league_team_count==32
    assert all(len(category.teams)==32 and category.eligible_team_count==31 for category in result.data)


@pytest.mark.parametrize('stage',['REG','POST','COMBINED'])
def test_single_query_population_stage_and_accepted_opponent_join(stage):
    filters=RankingFilters(season=2025,season_type=stage)
    compiled=league_query(filters).compile(dialect=dialect())
    sql=str(compiled)
    assert 'team_stats_pairs.id = team_stats_accepted.pair_id' in sql
    assert sql.count('JOIN team_game_stat_revisions AS')==2
    assert 'scheduled' in sql and 'LEFT OUTER JOIN totals' in sql
    assert 'count(accepted.net_passing_yards)' in sql and 'sum(accepted.net_passing_yards)' in sql
    assert 2025 in compiled.params.values()
    assert (stage in compiled.params.values())==(stage!='COMBINED')
    for forbidden in ('raw_source_record','review_token','team_stats_batches','team_stats_selection_events'):
        assert forbidden not in sql
    repository=TeamRankingsRepository(Mock())
    repository.league(filters)
    repository.session.execute.assert_called_once()


@pytest.mark.parametrize('query',[
    '', 'season=2023','season=2027','season=abc','season=2026&season_type=ALL',
    'season=2026&category=overall','season=2026&team_id=bad',
    'season=2026&season=2025','season=2026&season_type=REG&season_type=POST',
    'season=2026&cutoff=PRIVATE_VALUE','season=2026&week=1'])
def test_http_invalid_query(query):
    app=application()
    async def unused():return None
    app.dependency_overrides[get_team_rankings_service]=unused
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as c:
            return await c.get('/api/team-rankings?'+query)
    response=asyncio.run(request())
    assert response.status_code==422 and response.json()['error']['code']=='VALIDATION_ERROR'
    assert 'PRIVATE_VALUE' not in response.text


@pytest.mark.parametrize('method',['POST','PUT','PATCH','DELETE'])
def test_read_only_http_methods(method):
    async def request():
        async with AsyncClient(transport=ASGITransport(app=application()),base_url='http://test') as c:
            return await c.request(method,'/api/team-rankings?season=2026')
    response=asyncio.run(request())
    assert response.status_code==405 and response.json()['error']['code']=='METHOD_NOT_ALLOWED'


@pytest.mark.parametrize('failure,status,code',[
    (TeamNotFound(),404,'TEAM_NOT_FOUND'),
    (OperationalError('PRIVATE_SQL',{},Exception('PRIVATE_DETAILS')),503,'DATABASE_UNAVAILABLE')])
def test_http_error_contract(failure,status,code):
    app=application()
    async def fail():raise failure
    app.dependency_overrides[get_team_rankings_service]=fail
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as c:
            return await c.get('/api/team-rankings?season=2026')
    response=asyncio.run(request())
    assert response.status_code==status and response.json()['error']['code']==code
    assert 'PRIVATE' not in response.text


def test_openapi_documents_defaults_and_safe_response():
    schema=application().openapi()
    route=schema['paths']['/api/team-rankings']
    assert set(route)=={'get'}
    assert next(p for p in route['get']['parameters'] if p['name']=='season_type')['schema']['default']=='REG'
    assert 'raw_source_record' not in str(schema)


@pytest.mark.api
def test_http_success_serialization():
    repo=Mock();repo.league.return_value=[row('AAA',100),row('BBB',200)]
    app=application();app.dependency_overrides[get_team_rankings_service]=lambda:TeamRankingsService(repo)
    with TestClient(app) as c:
        response=c.get('/api/team-rankings?season=2026&category=passing_offense')
        assert response.status_code==200 and set(response.json())=={'data','meta'}
        assert response.json()['data'][0]['teams'][0]['team']['code']=='BBB'
        assert response.json()['meta']['filters']['season_type']=='REG'
        response=c.get('/api/team-rankings?season=2026&season_type=COMBINED')
        assert response.status_code==200 and len(response.json()['data'])==4


@pytest.mark.database
def test_actual_nfl_api_rank_query_and_unchanged_denied_permissions(pg_engine):
    from pydantic import SecretStr
    from app.db.session import make_engine
    settings=Settings().model_copy(update=dict(db_user='nfl_api',db_password=SecretStr('SYNTHETIC_API_PASSWORD_123456789'),db_purpose='runtime'))
    engine=make_engine(settings)
    try:
        with engine.connect() as c,c.begin():
            assert c.scalar(text('SELECT session_user'))=='nfl_api'
            for stage in ('REG','POST','COMBINED'):
                c.execute(league_query(RankingFilters(season=2026,season_type=stage))).all()
            for sql in ('SELECT raw_source_record FROM team_game_stat_revisions',
                'SELECT review_token FROM team_stats_batches','TRUNCATE team_stats_accepted',
                'UPDATE games SET status=status','ALTER TABLE team_stats_accepted DISABLE TRIGGER ALL'):
                with pytest.raises(DBAPIError) as exc:
                    with c.begin_nested():c.exec_driver_sql(sql)
                assert exc.value.orig.sqlstate=='42501'
    finally:engine.dispose()


@pytest.mark.database
def test_populated_accepted_net_opponent_and_stage_rankings(db_candidate):
    from test_team_stats_ingestion import approved_import
    from app.models import Game,TeamStatsPair,TeamGameStatRevision,TeamStatsBatch
    s=db_candidate[0];approved_import(db_candidate)
    service=TeamRankingsService(TeamRankingsRepository(s))
    result=service.rankings(RankingFilters(season=2024))
    assert result.meta.league_team_count==32 and result.meta.accepted_games==272
    assert result.meta.coverage_complete_for_stored_schedule
    for category in result.data:
        assert len(category.teams)==32
        assert all(team.rank==1 for team in category.teams)
        expected=190 if category.category.startswith('passing') else 0
        assert all(team.average==expected for team in category.teams)
    # A complete unaccepted revision must not change standings or averages.
    game=s.scalar(select(Game).where(Game.season==2024,Game.season_type=='REG').limit(1))
    old=s.scalar(select(TeamStatsPair).where(TeamStatsPair.game_id==game.id))
    batch=TeamStatsBatch(kind='IMPORT',candidate_sha256='d'*64,review_token='e'*64,evidence={})
    s.add(batch);s.flush()
    never=TeamStatsPair(game_id=game.id,home_team_id=game.home_team_id,away_team_id=game.away_team_id,
        batch_id=batch.id,source_artifact_id=old.source_artifact_id,previous_pair_id=old.id,
        definition_version=old.definition_version,content_sha256='f'*64)
    s.add(never);s.flush()
    for original in s.scalars(select(TeamGameStatRevision).where(TeamGameStatRevision.pair_id==old.id)):
        values={col.name:getattr(original,col.name) for col in original.__table__.columns}
        values.update(pair_id=never.id,gross_passing_yards=999,original_sack_yards=-1,net_passing_yards=998,rushing_yards=999)
        s.add(TeamGameStatRevision(**values))
    s.flush()
    assert service.rankings(RankingFilters(season=2024)).model_dump()==result.model_dump()
    post=service.rankings(RankingFilters(season=2024,season_type='POST'))
    combined=service.rankings(RankingFilters(season=2024,season_type='COMBINED'))
    assert post.meta.accepted_games==13 and combined.meta.accepted_games==285
    assert any(not team.eligible and team.rank is None for team in post.data[0].teams)
    assert service.rankings(RankingFilters(season=2026,season_type='POST')).meta.accepted_games==0
    # New stored schedule game without stats makes coverage partial, never a zero performance.
    s.add(Game(provider='nflverse',source_game_id='synthetic-extra-2026',season=2026,season_type='REG',week=18,
        game_type='REG',home_team_id=game.home_team_id,away_team_id=game.away_team_id,
        source_home_team=game.source_home_team,source_away_team=game.source_away_team,
        source_artifact_id=game.source_artifact_id,source_record_sha256='a'*64))
    s.flush()
    partial=service.rankings(RankingFilters(season=2026))
    assert partial.meta.missing_statistics_games==1 and not partial.meta.coverage_complete_for_stored_schedule
    assert all(t.average==190 for t in partial.data[0].teams)
    # Same uncommitted synthetic rows, restricted SQL privileges; actual login tested separately above.
    s.execute(text('SET LOCAL ROLE nfl_api'))
    assert service.rankings(RankingFilters(season=2024)).meta.accepted_games==272
    s.execute(text('RESET ROLE'))


from test_team_stats_ingestion import db_candidate
from test_ingestion import source_rows


@pytest.mark.database
def test_varied_accepted_offense_maps_to_opponent_defense(db_candidate,tmp_path):
    from test_team_stats_ingestion import make_files
    from ingestion.team_stats.candidate import load_candidate,archive_candidate
    from ingestion.team_stats.storage import inspect,plan_import,apply_import
    from app.models import Game
    s,_,_,_,rows,identities=db_candidate
    game=s.scalar(select(Game).where(Game.season==2024,Game.week==2,Game.season_type=='REG').limit(1))
    def vary(year,records):
        if year!=2024:return
        for record in records:
            if record['game_id']==game.source_game_id:
                home=record['team']==game.source_home_team
                record.update(passing_yards='350' if home else '100',sack_yards_lost='-20' if home else '-5',
                              rushing_yards='33' if home else '-4')
    candidate=load_candidate(**make_files(tmp_path/'varied',rows,identities,vary))
    archives=archive_candidate(candidate,tmp_path/'captures')
    plan=plan_import(inspect(s),candidate)
    apply_import(s,candidate,archives,plan['review_token'])
    service=TeamRankingsService(TeamRankingsRepository(s))
    result=service.rankings(RankingFilters(season=2024))
    categories={category.category:{t.team.id:t for t in category.teams} for category in result.data}
    home=categories['passing_offense'][game.home_team_id]
    away=categories['passing_offense'][game.away_team_id]
    home_defense=categories['passing_defense'][game.home_team_id]
    away_defense=categories['passing_defense'][game.away_team_id]
    assert home.total_yards==190*(home.games_with_values-1)+330
    assert away.total_yards==190*(away.games_with_values-1)+95
    assert home_defense.total_yards==190*(home_defense.games_with_values-1)+95
    assert away_defense.total_yards==190*(away_defense.games_with_values-1)+330
    assert home.rank==1 and home_defense.rank==1
    assert categories['rushing_offense'][game.home_team_id].total_yards==33
    assert categories['rushing_defense'][game.home_team_id].total_yards==-4


def test_metric_denominator_is_not_all_accepted_games():
    sample=row('AAA',370,count=5,scheduled=7)
    sample['passing_offense_count']=2
    result=rank_category([sample],'passing_offense').teams[0]
    assert result.average==185 and result.games_with_values==2
    assert result.games_with_accepted_statistics==5 and result.missing_metric_games==3
    assert result.missing_statistics_games==2
