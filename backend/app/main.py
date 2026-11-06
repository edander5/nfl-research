from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router
from app.core.config import Settings
from app.db.session import make_engine


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
    app.include_router(router)
    return app
