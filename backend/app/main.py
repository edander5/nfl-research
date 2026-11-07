from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.api.errors import database_unavailable, http_error, invalid_request, missing_game
from app.api.schedule import router as schedule_router
from app.api.health import router
from app.core.config import Settings
from app.db.session import make_engine
from app.services.schedule import GameNotFound


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
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_exception_handler(SQLAlchemyError, database_unavailable)
    app.add_exception_handler(GameNotFound, missing_game)
    app.include_router(router)
    app.include_router(schedule_router)
    return app
