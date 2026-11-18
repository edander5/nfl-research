"""Synthetic real-SQL and typed/HTTP research tests; no production data or imports."""
import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select, text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import OperationalError

from app.api.team_stats import game_research, get_game_research_service
from app.models import Game, TeamGameStatRevision, TeamStatsAccepted, TeamStatsPair
from app.repositories.game_research import GameResearchRepository, game_research_query
from app.schemas.game_research import GameResearchFilters, GameResearchResponse
from app.services.game_research import GameResearchService
from app.services.schedule import GameNotFound
from app.services.team_stats import InvalidTrendMatchup, TeamNotFound
from test_team_trends import application, dataset


def research(data, *, team=None, **changes):
    session, _, subject, *_ = data
    return GameResearchService(GameResearchRepository(session)).research(team or subject,
        GameResearchFilters(season=changes.pop('season',2026), season_type=changes.pop('season_type','REG'), **changes))


def anchor(data, **changes):
    return data[-1](22, accepted=False, kickoff=datetime(2030,1,1,tzinfo=timezone.utc), **changes)[0]


@pytest.mark.parametrize('window,size', [('L3',3),('L5',5),('L10',10),('L20',20),('SEASON',21)])
def test_windows_real_sql_combined_scores_order_and_summary(dataset,window,size):
    add=dataset[-1]
    ids={i:add(i,scores=(i,21),home=i%2==0)[0] for i in reversed(range(1,22))}
    result=research(dataset,matchup_id=anchor(dataset),window=window,line='31',side='OVER')
    data=result.data
    expected=list(range(21,21-size,-1))
    assert [game.game_id for game in data.observations]==[ids[i] for i in expected]
    assert [game.combined_points for game in data.observations]==[i+21 for i in expected]
    for index,game in zip(expected,data.observations):
        assert game.reported_points_scored==(index if index%2==0 else 21)
        assert game.reported_points_allowed==(21 if index%2==0 else index)
        assert game.side==('HOME' if index%2==0 else 'AWAY')
        assert game.scores_available and game.status=='UNKNOWN' and game.score_finality=='UNVERIFIED'
        assert game.provenance.provider=='nflverse' and game.accepted_pair_id
    assert data.summary.eligible_game_count==size and data.summary.games_with_usable_scores==size
    assert data.summary.average_combined_points==sum(i+21 for i in expected)/size
    assert data.summary.over_count==sum(i+21>31 for i in expected)
    assert data.summary.under_count==sum(i+21<31 for i in expected)
    assert data.summary.push_count==sum(i+21==31 for i in expected)
    assert data.summary.hit_rate==data.summary.over_count/size
    assert data.summary.hit_rate_denominator==size
    assert data.requested_game_count==(None if window=='SEASON' else size)
    assert result.meta.available_eligible_games==21 and result.meta.window_complete
    assert not result.meta.cross_season and not result.meta.completion_before_cutoff_verified


@pytest.mark.parametrize('window',['L3','L5','L10','L20'])
def test_short_samples_missing_scores_and_zero_not_under(dataset,window):
    add=dataset[-1]
    add(1,scores=(99,99))  # Older game cannot backfill L3's missing-score slot.
    missing,_=add(2,scores=(None,None))
    zero,_=add(3,scores=(0,0))
    partial,_=add(4,scores=(None,10))  # Synthetic damaged score pair: must remain unknown.
    result=research(dataset,matchup_id=anchor(dataset),window=window,line='0')
    summary=result.data.summary
    assert summary.eligible_game_count==(3 if window=='L3' else 4)
    assert summary.games_without_usable_scores==2
    assert summary.games_with_usable_scores==(1 if window=='L3' else 2)
    by_id={game.game_id:game for game in result.data.observations}
    assert by_id[missing].combined_points is None and by_id[partial].outcome=='UNDETERMINED'
    assert by_id[zero].combined_points==0 and by_id[zero].outcome=='PUSH'
    assert summary.under_count==0 and summary.push_count==1
    assert result.meta.scores_complete is False
    assert result.meta.window_complete==(window=='L3')


@pytest.mark.parametrize('line,outcome', [('43.999999','OVER'),('44','PUSH'),('44.000001','UNDER')])
def test_exact_decimal_classification_and_reference_is_independent(dataset,line,outcome):
    dataset[-1](1,scores=(20,24),reference='40.5')
    result=research(dataset,matchup_id=anchor(dataset),line=line)
    observation=result.data.observations[0]
    assert observation.outcome==outcome
    assert result.data.line==Decimal(line) and result.data.threshold_origin=='MANUAL'
    assert observation.reference_total.line==Decimal('40.5') and observation.reference_total.outcome=='OVER'
    reference=observation.reference_total
    assert reference.bookmaker is None and reference.quote_updated_at is None and reference.freshness=='UNKNOWN'
    assert reference.classification=='UNVERIFIED_SOURCE_REFERENCE'
    assert reference.provenance.artifact_retrieved_at is None
    assert reference.provenance.source_record_sha256


def test_push_in_denominator_side_symmetry_all_push_and_no_line(dataset):
    add=dataset[-1]
    add(1,scores=(20,25));add(2,scores=(20,24));add(3,scores=(20,23))
    matchup=anchor(dataset)
    over=research(dataset,matchup_id=matchup,line='44').data.summary
    under=research(dataset,matchup_id=matchup,line='44',side='UNDER').data.summary
    assert (over.over_count,over.under_count,over.push_count)==(1,1,1)
    assert over.hit_rate==under.hit_rate==1/3 and over.hit_rate_denominator==3
    assert over.hit_rate_denominator_policy=='usable_scores_including_pushes'
    absent=research(dataset,matchup_id=matchup)
    assert absent.data.summary.average_combined_points==44
    assert absent.data.summary.over_count is absent.data.summary.under_count is absent.data.summary.push_count is None
    assert absent.data.summary.hit_rate is absent.data.summary.hit_rate_denominator is None
    assert absent.data.summary.outcomes_unavailable_reason=='threshold_required'
    assert all(game.outcome_unavailable_reason=='threshold_required' for game in absent.data.observations)
    # Replace only synthetic score fixtures to check an all-push sample, never production data.
    session,tables,*_=dataset
    session.execute(tables[Game].update().values(reported_home_score=20,reported_away_score=24))
    pushes=research(dataset,matchup_id=matchup,line='44').data.summary
    assert pushes.push_count==3 and pushes.hit_rate==0 and pushes.hit_rate_denominator==3


@pytest.mark.parametrize('season',[2024,2025,2026])
@pytest.mark.parametrize('stage',['REG','POST'])
def test_season_and_h2h_scopes_never_mix_seasons_stages_or_opponents(dataset,season,stage):
    _,_,_,opponent,stranger,add=dataset
    for year in (2024,2025,2026):
        for kind in ('REG','POST'):
            add(1,season=year,stage=kind,scores=(20,21))
            add(2,season=year,stage=kind,scores=(20,22),opponent_id=stranger)
    matchup=anchor(dataset,season=season,stage=stage)
    h2h=research(dataset,season=season,season_type=stage,matchup_id=matchup,window='H2H')
    full=research(dataset,season=season,season_type=stage,matchup_id=matchup,window='SEASON')
    assert h2h.data.opponent_id==opponent and h2h.data.requested_game_count is None
    assert len(h2h.data.observations)==1 and len(full.data.observations)==2
    assert all(game.opponent.id==opponent and game.season==season and game.season_type==stage for game in h2h.data.observations)
    assert h2h.meta.scheduled_games_in_scope==1 and h2h.meta.accepted_games_in_scope==1


@pytest.mark.parametrize('upcoming',[True,False])
def test_anchor_cutoff_same_time_later_unknown_dates_and_accepted_only(dataset,upcoming):
    *_,add=dataset
    early=add(1,scores=(20,21))[0]
    when=datetime(2030 if upcoming else 2026,11,1,tzinfo=timezone.utc)
    matchup=add(10,scores=(20,22),accepted=not upcoming,kickoff=when)[0]
    add(11,kickoff=when);add(12,kickoff=when+timedelta(days=1));add(13,dated=False)
    add(2,accepted=False);add(3,reciprocal=False);add(4,provider='different')
    result=research(dataset,matchup_id=matchup,window='SEASON',line='40.5')
    assert [game.game_id for game in result.data.observations]==[early]
    assert result.meta.excluded_at_or_after_matchup_games==(2 if upcoming else 3)
    assert result.meta.excluded_unknown_kickoff_games==1
    assert result.meta.scheduled_games_without_accepted_statistics==2


def test_empty_unavailable_and_bad_matchup_context(dataset):
    session,tables,team,opponent,stranger,add=dataset
    first=add(1,scores=(20,21),opponent_id=stranger)[0]
    empty=research(dataset,matchup_id=first,line='44')
    assert empty.data.availability=='EMPTY' and empty.meta.unavailable_reason=='no_eligible_games'
    assert empty.data.summary.games_with_usable_scores==0 and empty.data.summary.average_combined_points is None
    assert empty.data.summary.hit_rate is None and empty.data.summary.over_count==0
    h2h=research(dataset,matchup_id=anchor(dataset),window='H2H')
    assert h2h.meta.unavailable_reason=='no_h2h_games' and not h2h.data.observations
    unknown=add(3,dated=False)[0]
    withheld=research(dataset,matchup_id=unknown)
    assert withheld.data.availability=='UNAVAILABLE' and withheld.meta.unavailable_reason=='matchup_kickoff_unknown'
    assert not withheld.data.observations
    with pytest.raises(GameNotFound):research(dataset,matchup_id=uuid4())
    with pytest.raises(TeamNotFound):research(dataset,team=uuid4(),matchup_id=first)
    with pytest.raises(InvalidTrendMatchup):research(dataset,team=opponent,matchup_id=first)
    with pytest.raises(InvalidTrendMatchup):research(dataset,season=2025,matchup_id=first)
    with pytest.raises(InvalidTrendMatchup):research(dataset,season_type='POST',matchup_id=first)
    # Impossible under real NOT NULL/FK constraints, but explicitly unavailable if opponent identity is absent.
    session.execute(tables[Game].update().where(tables[Game].c.id==first).values(away_team_id=None))
    unverified=research(dataset,matchup_id=first,window='H2H')
    assert unverified.data.availability=='UNAVAILABLE' and unverified.meta.unavailable_reason=='opponent_identity_unknown'


@pytest.mark.parametrize('reference',[None,'','NA','garbage','-1','44.0000001',False])
def test_missing_invalid_reference_does_not_remove_scored_observations(dataset,reference):
    dataset[-1](1,scores=(20,24),reference=reference)
    result=research(dataset,matchup_id=anchor(dataset),line='43.5')
    assert result.data.summary.games_with_usable_scores==1 and result.data.summary.over_count==1
    assert result.data.observations[0].reference_total.line is None
    assert result.data.observations[0].reference_total.unavailable_reason
    assert result.meta.games_without_reference_total==1 and not result.meta.references_complete


@pytest.mark.parametrize('problem',['missing_raw','hash','identity'])
def test_reference_identity_and_hash_safeguards(dataset,problem):
    session,tables,*_=dataset
    game_id,_=dataset[-1](1,scores=(20,24))
    if problem=='missing_raw': changes=dict(raw_source_record=None)
    elif problem=='hash': changes=dict(source_record_sha256='0'*64)
    else:
        raw=dict(session.scalar(select(tables[Game].c.raw_source_record).where(tables[Game].c.id==game_id)))
        raw['game_id']='not-the-selected-game'
        sha=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        changes=dict(raw_source_record=raw,source_record_sha256=sha)
    session.execute(tables[Game].update().where(tables[Game].c.id==game_id).values(**changes))
    result=research(dataset,matchup_id=anchor(dataset),line='44')
    ref=result.data.observations[0].reference_total
    assert ref.line is None and ref.unavailable_reason
    assert result.data.summary.push_count==1


def test_known_reference_without_scores_and_all_null_sample(dataset):
    dataset[-1](1)
    result=research(dataset,matchup_id=anchor(dataset),line='44.5')
    game=result.data.observations[0]
    assert game.reference_total.line==Decimal('44.5') and game.reference_total.outcome=='UNDETERMINED'
    assert game.outcome=='UNDETERMINED' and game.outcome_unavailable_reason=='scores_unavailable'
    summary=result.data.summary
    assert summary.over_count==summary.under_count==summary.push_count==0
    assert summary.hit_rate is None and summary.hit_rate_denominator==0
    assert summary.outcomes_unavailable_reason=='no_usable_scores'


def test_l20_of_one_regular_season_does_not_borrow_prior_season(dataset):
    for index in range(1,18):dataset[-1](index,scores=(20,index))
    dataset[-1](18,season=2025,scores=(99,99))
    result=research(dataset,matchup_id=anchor(dataset),window='L20',line='44.5')
    assert result.data.summary.eligible_game_count==17
    assert result.data.requested_game_count==20 and not result.meta.window_complete
    assert all(game.season==2026 for game in result.data.observations)


def test_final_evidence_is_preserved_without_pregame_certification(dataset):
    session,tables,*_=dataset
    game_id,_=dataset[-1](1,scores=(20,24))
    session.execute(tables[Game].update().where(tables[Game].c.id==game_id).values(
        status='FINAL',final_evidence_url='https://example.invalid/synthetic-final',
        final_verified_at=datetime(2026,11,1,tzinfo=timezone.utc)))
    result=research(dataset,matchup_id=anchor(dataset),line='44')
    assert result.data.observations[0].status=='FINAL'
    assert result.data.observations[0].score_finality=='CONFIRMED_FINAL'
    assert result.meta.selected_unknown_status_games==result.meta.selected_unverified_score_games==0
    assert not result.meta.completion_before_cutoff_verified and not result.meta.reference_lines_verified_pregame


def test_stable_ties_selected_ids_query_bound_read_only_and_private_fields(dataset):
    session,tables,team,_,_,add=dataset
    when=datetime(2026,10,1,tzinfo=timezone.utc)
    ids={i:add(i,kickoff=when,scores=(20,i))[0] for i in (1,3,4,2)}
    matchup=anchor(dataset)
    before={model:[dict(row) for row in session.execute(select(table)).mappings()] for model,table in tables.items()}
    statements=[]
    def capture(connection,cursor,statement,params,context,many):statements.append(statement)
    event.listen(session.bind,'before_cursor_execute',capture)
    try:
        for line in ('21','25.000001'):
            response=research(dataset,matchup_id=matchup,window='L3',line=line)
            assert [g.game_id for g in response.data.observations]==[ids[4],ids[3],ids[2]]
    finally:event.remove(session.bind,'before_cursor_execute',capture)
    assert len(statements)==4 and all(statement.lstrip().startswith(('SELECT','WITH')) for statement in statements)
    after={model:[dict(row) for row in session.execute(select(table)).mappings()] for model,table in tables.items()}
    assert before==after
    payload=response.model_dump_json()
    for private in ('reference_raw_record','raw_source_record','batch_id','review_token','artifact_path'):
        assert private not in payload
    sql=game_research_query(team,GameResearchFilters(season=2026,season_type='REG',matchup_id=matchup,window='L20')).compile(dialect=dialect())
    assert 'LIMIT' in str(sql) and 20 in sql.params.values()
    assert str(sql).count('JOIN team_game_stat_revisions AS')==2
    assert 'team_game_stat_revisions_1.raw_source_record' not in str(sql)
    assert 'team_stats_selection_events' not in str(sql)


def test_accepted_correction_pointer_does_not_duplicate_history(dataset):
    session,tables,*_=dataset
    game_id,pair_id=dataset[-1](1,scores=(20,24))
    matchup=anchor(dataset)
    old=dict(session.execute(select(tables[TeamStatsPair]).where(tables[TeamStatsPair].c.id==pair_id)).mappings().one())
    new_pair=uuid4();old['id']=new_pair
    session.execute(tables[TeamStatsPair].insert(),old)
    for original in session.execute(select(tables[TeamGameStatRevision]).where(tables[TeamGameStatRevision].c.pair_id==pair_id)).mappings().all():
        session.execute(tables[TeamGameStatRevision].insert(),dict(original,pair_id=new_pair))
    assert research(dataset,matchup_id=matchup).data.observations[0].accepted_pair_id==pair_id
    session.execute(tables[TeamStatsAccepted].update().where(tables[TeamStatsAccepted].c.game_id==game_id).values(pair_id=new_pair,generation=2))
    response=research(dataset,matchup_id=matchup)
    assert len(response.data.observations)==1 and response.data.observations[0].accepted_pair_id==new_pair
    assert response.data.observations[0].selection_generation==2


async def request(app,path,method='GET'):
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        return await client.request(method,path)


@pytest.mark.parametrize('query',[
    '', 'season=2023&season_type=REG', 'season=2027&season_type=REG', 'season=2026&season_type=COMBINED',
    'season=2026&season_type=REG&matchup_id=bad', 'season=2026&season_type=REG&window=ALL',
    'season=2026&season_type=REG&window=L5&window=L10', 'season=2026&season_type=REG&side=ALL',
    'season=2026&season_type=REG&period=FIRST_HALF', 'season=2026&season_type=REG&market=TEAM_TOTAL',
    'season=2026&season_type=REG&line=-1', 'season=2026&season_type=REG&line=NaN',
    'season=2026&season_type=REG&line=Infinity', 'season=2026&season_type=REG&line=1000001',
    'season=2026&season_type=REG&line=44.0000001', 'season=2026&season_type=REG&cross_season=true',
    'season=2026&season_type=REG&cutoff=PRIVATE_VALUE', 'season=2026&season_type=REG&line=44&line=45',
])
def test_invalid_http_filters(query):
    app=application()
    async def unused():return None
    app.dependency_overrides[get_game_research_service]=unused
    # Preserve an explicitly bad matchup, otherwise add a valid UUID for validation-only trials.
    if query and 'matchup_id=' not in query:query+='&matchup_id='+str(uuid4())
    response=asyncio.run(request(app,f'/api/teams/{uuid4()}/game-research?'+query))
    assert response.status_code==422 and response.json()['error']['code']=='VALIDATION_ERROR'
    assert 'PRIVATE_VALUE' not in response.text


def test_matchup_required_invalid_team_uuid_and_decimal_zero_allowed():
    app=application()
    async def unused():return None
    app.dependency_overrides[get_game_research_service]=unused
    for path in (f'/api/teams/{uuid4()}/game-research?season=2026&season_type=REG',
                 f'/api/teams/bad/game-research?season=2026&season_type=REG&matchup_id={uuid4()}'):
        assert asyncio.run(request(app,path)).status_code==422
    assert GameResearchFilters(season=2026,season_type='REG',matchup_id=uuid4(),line='0').line==Decimal(0)


@pytest.mark.parametrize('failure,status,code',[(TeamNotFound(),404,'TEAM_NOT_FOUND'),(GameNotFound(),404,'GAME_NOT_FOUND'),
    (InvalidTrendMatchup(),422,'VALIDATION_ERROR'),(OperationalError('PRIVATE',{},Exception('PRIVATE')),503,'DATABASE_UNAVAILABLE')])
def test_errors_and_read_only_methods(failure,status,code):
    app=application()
    async def fail():raise failure
    app.dependency_overrides[get_game_research_service]=fail
    path=f'/api/teams/{uuid4()}/game-research?season=2026&season_type=REG&matchup_id={uuid4()}'
    response=asyncio.run(request(app,path))
    assert response.status_code==status and response.json()['error']['code']==code and 'PRIVATE' not in response.text
    for method in ('POST','PUT','PATCH','DELETE'):
        assert asyncio.run(request(app,path,method)).status_code==405


def test_direct_typed_route_and_openapi(dataset):
    dataset[-1](1,scores=(20,24))
    filters=GameResearchFilters(season=2026,season_type='REG',matchup_id=anchor(dataset),line='44.000001')
    response=game_research(dataset[2],filters,GameResearchService(GameResearchRepository(dataset[0])))
    parsed=GameResearchResponse.model_validate_json(response.model_dump_json())
    assert parsed.data.line==Decimal('44.000001') and parsed.data.summary.under_count==1
    schema=application().openapi()
    route=schema['paths']['/api/teams/{team_id}/game-research']
    assert set(route)=={'get'}
    assert route['get']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('GameResearchResponse')
    assert 'reference_raw_record' not in str(schema)


@pytest.mark.api
def test_success_http_serialization(dataset):
    dataset[-1](1,scores=(20,24))
    team=dataset[2];matchup=anchor(dataset)
    data=research(dataset,matchup_id=matchup,line='44.000001')
    service=Mock();service.research.return_value=data
    app=application();app.dependency_overrides[get_game_research_service]=lambda:service
    with TestClient(app) as client:
        response=client.get(f'/api/teams/{team}/game-research?season=2026&season_type=REG&matchup_id={matchup}&line=44.000001')
        assert response.status_code==200 and response.json()['data']['line']=='44.000001'
        assert response.json()['data']['observations'][0]['outcome']=='UNDER'


@pytest.mark.database
def test_postgresql_research_query_existing_api_permissions(pg_engine):
    """Separately approved isolated runtime only; pg_engine provisions/migrates."""
    from pydantic import SecretStr
    from app.core.config import Settings
    from app.db.session import make_engine
    settings=Settings().model_copy(update=dict(db_user='nfl_api',
        db_password=SecretStr('SYNTHETIC_API_PASSWORD_123456789'),db_purpose='runtime'))
    engine=make_engine(settings)
    try:
        with engine.connect() as connection,connection.begin():
            assert connection.scalar(text('SELECT session_user'))=='nfl_api'
            for window in ('L3','L5','L10','L20','SEASON','H2H'):
                for stage in ('REG','POST'):
                    row=connection.execute(game_research_query(uuid4(),GameResearchFilters(
                        season=2026,season_type=stage,matchup_id=uuid4(),window=window))).mappings().one()
                    assert row['game_id'] is None and row['eligible_count']==0
    finally:engine.dispose()
