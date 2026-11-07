"""All records here are synthetic fixtures, never production schedule data."""
import os
from datetime import date, datetime, time, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

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


# Synthetic HTTP/service fixture, intentionally independent of PostgreSQL.
@pytest.fixture
def api_game():
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    artifact = SimpleNamespace(id=uuid4(), sha256='a'*64, origin_status='DECLARED',
        documented_source_url='https://example.invalid/synthetic-source', declared_source_url=None,
        source_revision=None, publisher_sha256='b'*64, origin_verified_at=None, verification_method=None,
        provider_published_at=None, retrieved_at=None, recorded_at=now,
        license_url='https://creativecommons.org/licenses/by/4.0/', attribution='Synthetic test data',
        artifact_path='/private/never-return.csv', provenance_notes='private raw receipt')
    return SimpleNamespace(id=uuid4(), provider='nflverse', source_game_id='synthetic-game',
        season=2026, season_type='REG', week=9, game_type='REG',
        home_team=SimpleNamespace(id=uuid4(), code='AAA', name='Synthetic Home'),
        away_team=SimpleNamespace(id=uuid4(), code='BBB', name='Synthetic Away'),
        scheduled_kickoff_utc=now, source_gameday=date(2026,11,7), source_gametime=time(12),
        source_timezone='America/New_York', reported_home_score=0, reported_away_score=7,
        status='UNKNOWN', final_evidence_url=None, final_verified_at=None,
        neutral_site=None, overtime=None, updated_at=now, source_artifact=artifact,
        source_record_sha256='c'*64, source_line=2)
