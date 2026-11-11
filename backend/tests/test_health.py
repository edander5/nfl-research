from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app


def make_client():
    # Deliberately synthetic, unreachable host: liveness must not connect.
    settings = Settings(
        db_host="synthetic.invalid", db_name="nfl_research_test",
        db_user="synthetic", db_password="SYNTHETIC_NOT_A_REAL_SECRET",
    )
    return TestClient(create_app(settings))


def test_liveness_without_database():
    with make_client() as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_readiness_failure_is_sanitized():
    with make_client() as client:
        session = Mock()
        session.execute.side_effect = OperationalError("SELECT 1", {}, Exception("sensitive detail"))
        client.app.dependency_overrides[get_session] = lambda: session
        response = client.get("/api/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
        assert "sensitive" not in response.text


def test_readiness_checks_migration_revision():
    with make_client() as client:
        session = Mock()
        session.execute.return_value.scalar_one.return_value = "outdated_revision"
        client.app.dependency_overrides[get_session] = lambda: session
        assert client.get("/api/ready").status_code == 503
        session.execute.return_value.scalar_one.return_value = "0001_schedule"
        assert client.get("/api/ready").json() == {"status": "ready"}


def test_readiness_accepts_additive_team_stats_revision():
    from app.api.health import ready
    from fastapi import Response
    session = Mock()
    session.execute.return_value.scalar_one.return_value = "0002_team_stats"
    response = Response()
    assert ready(response, session) == {"status": "ready"}
    assert response.status_code == 200
