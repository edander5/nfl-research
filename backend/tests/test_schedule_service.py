"""Synthetic in-memory unit fixtures; no database, source artifact or HTTP server."""
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.main import create_app
from app.repositories.schedule import ScheduleRepository
from app.schemas.schedule import ScheduleFilters
from app.services.schedule import GameNotFound, ScheduleService, game_view



def coverage_row(season=2026, stage='REG', week=9, kind='REG'):
    return dict(season=season, season_type=stage, week=week, game_type=kind, game_count=1,
        reported_score_pairs=1, unknown_status_games=1, final_status_games=0,
        unknown_kickoff_games=0, unverified_origin_games=1)


def test_preserves_unknown_reported_zero_and_declared_origin(api_game):
    data = game_view(api_game).model_dump(mode='json')
    assert data['status'] == 'UNKNOWN' and data['score_finality'] == 'UNVERIFIED'
    assert data['reported_home_score'] == 0 and data['reported_away_score'] == 7
    assert data['final_evidence'] is None
    assert data['provenance']['origin_status'] == 'DECLARED'
    assert data['provenance']['retrieved_at'] is None
    assert data['provenance']['publisher_sha256'] != data['provenance']['artifact_sha256']
    assert 'artifact_path' not in data['provenance'] and 'provenance_notes' not in data['provenance']


def test_missing_values_remain_null(api_game):
    api_game.reported_home_score = api_game.reported_away_score = None
    api_game.scheduled_kickoff_utc = api_game.source_gameday = api_game.source_gametime = None
    data = game_view(api_game)
    assert data.reported_home_score is None and data.scheduled_kickoff_utc is None
    assert data.status == 'UNKNOWN' and data.score_finality == 'NOT_REPORTED'


def test_final_only_from_stored_status_and_evidence(api_game):
    api_game.status = 'FINAL'
    api_game.final_evidence_url = 'https://example.invalid/explicit-synthetic-final'
    api_game.final_verified_at = api_game.updated_at
    data = game_view(api_game)
    assert data.score_finality == 'CONFIRMED_FINAL'
    assert data.final_evidence.url == api_game.final_evidence_url
    api_game.final_evidence_url = None
    with pytest.raises(ValidationError):
        game_view(api_game)


@pytest.mark.parametrize('parameters', [
    dict(season_type='REG',week=19), dict(season_type='REG',round='WC'),
    dict(season_type='POST',week=18), dict(season_type='POST',week=20,round='WC'),
    dict(season_type='reg'), dict(season_type='ALL'), dict(season_type='POST',round='BAD'),
    dict(season_type='REG',week=0),dict(season_type='REG',week=23),
    dict(season_type='REG',unexpected='x'), {},
])
def test_invalid_filters(parameters):
    with pytest.raises(ValidationError):
        ScheduleFilters(**parameters)


@pytest.mark.parametrize('stage,week,round_name,expected', [
    ('REG',None,None,None), ('REG',1,None,1), ('REG',18,None,18),
    ('POST',None,'WC',19), ('POST',20,'DIV',20), ('POST',None,'CON',21), ('POST',22,'SB',22),
])
def test_filter_mapping(api_game,stage,week,round_name,expected):
    repository = Mock()
    api_game.season_type = stage
    api_game.game_type = round_name or ('WC' if stage == 'POST' else 'REG')
    api_game.week = expected or (19 if stage == 'POST' else 1)
    repository.games.return_value = [api_game]
    response = ScheduleService(repository).schedule(2026,ScheduleFilters(season_type=stage,week=week,round=round_name))
    repository.games.assert_called_once_with(2026)
    assert len(response.data) == 1 and response.meta.returned_count == 1
    repository.coverage.assert_not_called()


def test_available_seasons_and_absent_postseason():
    repository = Mock()
    repository.coverage.return_value = [coverage_row(2025),coverage_row(2024),coverage_row(2026)]
    data = ScheduleService(repository).seasons()
    assert [s.season for s in data.data] == [2024,2025,2026]
    assert data.meta.missing_seasons == []
    assert data.data[2].coverage[1].season_type == 'POST'
    assert data.data[2].coverage[1].game_count == 0
    assert data.data[2].coverage[1].weeks == [] and data.data[2].coverage[1].rounds == []


def test_empty_database_does_not_invent_available_seasons():
    repository = Mock()
    repository.coverage.return_value = []
    response = ScheduleService(repository).seasons()
    assert response.data == [] and response.meta.missing_seasons == [2024,2025,2026]


def test_game_uuid_lookup(api_game):
    repository = Mock()
    repository.game.return_value = api_game
    result = ScheduleService(repository).game(api_game.id)
    assert result.data.id == api_game.id
    repository.game.assert_called_once_with(api_game.id)
    repository.game.return_value = None
    with pytest.raises(GameNotFound):
        ScheduleService(repository).game(api_game.id)


def test_repository_filters_and_deterministic_null_order():
    session = Mock()
    session.scalars.return_value.all.return_value = []
    ScheduleRepository(session).games(2026)
    sql = str(session.scalars.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert 'games.provider =' in sql and 'games.season =' in sql
    assert 'ORDER BY games.week, games.scheduled_kickoff_utc ASC NULLS LAST, games.source_game_id, games.id' in sql
    assert 'teams AS' in sql and 'source_artifacts AS' in sql  # Eager loading, no per-game lazy queries.
    session.flush.assert_not_called()
    session.commit.assert_not_called()


def test_openapi_contract_has_only_read_schedule_operations():
    app = create_app(Settings(db_host='synthetic.invalid',db_name='nfl_research_test',db_user='synthetic',db_password='SYNTHETIC_ONLY'))
    spec = app.openapi()
    for path in ['/api/seasons','/api/seasons/{season}/schedule','/api/games/{game_id}']:
        assert set(spec['paths'][path]) == {'get'}
        responses = spec['paths'][path]['get']['responses']
        assert {'200','422','503'} <= set(responses)
    assert '404' in spec['paths']['/api/games/{game_id}']['get']['responses']
    parameters = spec['paths']['/api/seasons/{season}/schedule']['get']['parameters']
    assert {p['name'] for p in parameters} == {'season','season_type','week','round'}
    assert next(p for p in parameters if p['name'] == 'season_type')['required']


@pytest.mark.parametrize('filters', [dict(season_type='POST'),dict(season_type='REG',week=10)])
def test_empty_filter_result_retains_season_coverage(api_game, filters):
    repository = Mock()
    repository.games.return_value = [api_game]
    result = ScheduleService(repository).schedule(2026,ScheduleFilters(**filters))
    assert result.data == [] and result.meta.returned_count == 0
    assert result.meta.season_coverage[0].game_count == 1
    assert result.meta.season_coverage[1].game_count == 0
