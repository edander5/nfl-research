from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Process liveness; does not imply database/schema readiness."""
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response, session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
        revision = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if revision not in ("0001_schedule", "0002_team_stats"):
            response.status_code = 503
            return {"status": "unavailable"}
    except SQLAlchemyError:
        # Never expose connection strings, credentials or SQL failure details.
        response.status_code = 503
        return {"status": "unavailable"}
    return {"status": "ready"}
