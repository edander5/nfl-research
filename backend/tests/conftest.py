"""All records here are synthetic fixtures, never production schedule data."""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import make_engine
from app.models import Game, SourceArtifact, Team


@pytest.fixture(scope="session")
def pg_engine():
    if os.environ.get("RUN_DATABASE_TESTS") != "1":
        pytest.skip("Set RUN_DATABASE_TESTS=1 and use isolated nfl_research_test PostgreSQL")
    settings = Settings()
    if settings.db_name != "nfl_research_test":
        pytest.fail("Refusing database tests outside nfl_research_test")
    engine = make_engine(settings)
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        # Additive upgrade only; no drop/create/reset or CSV load.
        with engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(pg_engine):
    with pg_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            try:
                yield session
            finally:
                session.close()
                transaction.rollback()


@pytest.fixture
def synthetic_game(db_session):
    home = Team(code="AAA", name="Synthetic Home")
    away = Team(code="BBB", name="Synthetic Away")
    artifact = SourceArtifact(
        provider="synthetic", artifact_path="synthetic://tests/fixture.csv",
        sha256="a" * 64, publisher_sha256="b" * 64, byte_size=100,
        provenance_notes="Synthetic fixture with deliberate checksum mismatch",
    )
    db_session.add_all([home, away, artifact])
    db_session.flush()

    def factory(**changes):
        values = dict(
            provider="synthetic", source_game_id="synthetic-game-1",
            season=2024, season_type="REG", game_type="REG", week=1,
            home_team_id=home.id, away_team_id=away.id,
            source_home_team="AAA", source_away_team="BBB",
            source_artifact_id=artifact.id, source_record_sha256="c" * 64,
        )
        values.update(changes)
        return Game(**values)

    return factory
