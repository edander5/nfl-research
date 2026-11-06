"""PostgreSQL constraint tests; all data is synthetic and rolled back."""
from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.models import Game, SourceArtifact, Team, TeamAlias

pytestmark = pytest.mark.database


def test_migration_matches_models(pg_engine):
    with pg_engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_relationships_and_unknown_defaults(db_session, synthetic_game):
    game = synthetic_game()
    db_session.add(game)
    db_session.flush()
    db_session.expire_all()
    loaded = db_session.get(Game, game.id)
    assert loaded.home_team.name == "Synthetic Home"
    assert loaded.away_team.name == "Synthetic Away"
    assert loaded.source_artifact.origin_status == "DECLARED"
    assert loaded.source_artifact.retrieved_at is None
    assert loaded.status == "UNKNOWN"
    assert loaded.reported_home_score is None
    assert loaded.reported_away_score is None
    assert loaded.scheduled_kickoff_utc is None


def test_provider_alias_relationship(db_session):
    team = Team(code="CCC", name="Synthetic Club")
    alias = TeamAlias(provider="synthetic", source_team_code="ALTERNATE", team=team)
    db_session.add(alias)
    db_session.flush()
    db_session.expire_all()
    assert db_session.get(TeamAlias, ("synthetic", "ALTERNATE")).team.id == team.id


def test_unique_provider_game_id(db_session, synthetic_game):
    db_session.add(synthetic_game())
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(synthetic_game())
        db_session.flush()


def test_old_game_id_is_nonunique(db_session, synthetic_game):
    one = synthetic_game(old_game_id="shared")
    two = synthetic_game(source_game_id="synthetic-game-2", old_game_id="shared")
    db_session.add_all([one, two])
    db_session.flush()
    assert one.id != two.id
    assert len(db_session.scalars(select(Game).where(Game.old_game_id == "shared")).all()) == 2


@pytest.mark.parametrize("field", [
    "provider", "source_game_id", "season", "season_type", "game_type", "week",
    "home_team_id", "away_team_id", "source_home_team", "source_away_team",
    "source_artifact_id", "source_record_sha256",
])
def test_required_game_fields(db_session, synthetic_game, field):
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(synthetic_game(**{field: None}))
        db_session.flush()


@pytest.mark.parametrize("values", [
    {"source_game_id": " "}, {"source_home_team": ""}, {"source_record_sha256": "bad"},
    {"season": 2023}, {"week": 19},
    {"season_type": "POST", "game_type": "WC", "week": 18},
    {"reported_home_score": 1},
    {"reported_home_score": -1, "reported_away_score": 0},
    {"status": "IN_PROGRESS"}, {"status": "POSTPONED"}, {"status": "FINAL"},
])
def test_invalid_domain_values_rejected(db_session, synthetic_game, values):
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(synthetic_game(**values))
        db_session.flush()


def test_foreign_key_rejects_unknown_team(db_session, synthetic_game):
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(synthetic_game(home_team_id=uuid4()))
        db_session.flush()


def test_same_team_rejected(db_session, synthetic_game):
    game = synthetic_game()
    game.away_team_id = game.home_team_id
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(game)
        db_session.flush()


def test_team_delete_is_restricted(db_session, synthetic_game):
    game = synthetic_game()
    db_session.add(game)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.delete(game.home_team)
        db_session.flush()


def test_missing_team_name_rejected(db_session):
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(insert(Team).values(id=uuid4(), code="DDD"))


def test_alias_cannot_point_to_two_teams(db_session):
    first = Team(code="DDD", name="Synthetic First")
    second = Team(code="EEE", name="Synthetic Second")
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add(TeamAlias(provider="synthetic", source_team_code="alias", team_id=first.id))
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(TeamAlias(provider="synthetic", source_team_code="alias", team_id=second.id))
        db_session.flush()


def test_past_kickoff_and_scores_do_not_finalize(db_session, synthetic_game):
    game = synthetic_game(
        source_gameday=date(2024, 9, 1), source_gametime=time(13),
        scheduled_kickoff_utc=datetime(2024, 9, 1, 17, tzinfo=timezone.utc),
        reported_home_score=0, reported_away_score=7,
    )
    db_session.add(game)
    db_session.flush()
    db_session.refresh(game)
    assert game.status == "UNKNOWN"
    assert game.reported_home_score == 0
    assert game.scheduled_kickoff_utc.utcoffset().total_seconds() == 0


def test_final_requires_explicit_evidence(db_session, synthetic_game):
    game = synthetic_game(
        status="FINAL", reported_home_score=0, reported_away_score=7,
        final_evidence_url="https://example.invalid/synthetic-final",
        final_verified_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(game)
    db_session.flush()
    assert game.status == "FINAL"


def test_postseason_round(db_session, synthetic_game):
    db_session.add(synthetic_game(season_type="POST", game_type="SB", week=22))
    db_session.flush()


def test_origin_is_not_authenticated_by_default(db_session, synthetic_game):
    game = synthetic_game()
    db_session.add(game)
    db_session.flush()
    artifact = game.source_artifact
    assert artifact.sha256 != artifact.publisher_sha256
    assert artifact.origin_status == "DECLARED"
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(update(SourceArtifact).where(SourceArtifact.id == artifact.id).values(
            origin_status="VERIFIED", origin_verified_at=datetime.now(timezone.utc),
            declared_source_url="https://example.invalid/synthetic-source", verification_method="synthetic",
        ))


def test_artifact_provider_must_match_game(db_session, synthetic_game):
    game = synthetic_game()
    db_session.add(game)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(update(Game).where(Game.id == game.id).values(provider="other-provider"))
