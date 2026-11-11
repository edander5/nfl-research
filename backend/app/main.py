from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.api.errors import database_unavailable, http_error, invalid_request, missing_game, missing_team
from app.api.team_stats import router as team_stats_router
from app.api.schedule import router as schedule_router
from app.api.freshness import router as freshness_router
from app.repositories.refresh_status import RefreshStatusRepository
from app.services.freshness import FreshnessService
from app.api.health import router
from app.core.config import Settings
from app.db.session import make_engine
from app.services.schedule import GameNotFound
from app.services.team_stats import TeamNotFound


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = make_engine(config)
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(title="NFL Research Development API", lifespan=lifespan)
    app.state.freshness_service = FreshnessService(
        RefreshStatusRepository(config.refresh_state_dir), config.refresh_stale_after_hours * 3600)
    app.include_router(freshness_router)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_exception_handler(SQLAlchemyError, database_unavailable)
    app.add_exception_handler(GameNotFound, missing_game)
    app.add_exception_handler(TeamNotFound, missing_team)
    app.include_router(router)
    app.include_router(schedule_router)
    app.include_router(team_stats_router)
    return app
