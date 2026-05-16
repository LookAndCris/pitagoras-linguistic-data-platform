from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.backend.app.api.routes.documents import router as documents_router
from apps.backend.app.api.routes.health import router as health_router
from packages.core.db import create_database_runtime, dispose_database_runtime
from packages.core.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = create_database_runtime(app.state.settings)
        app.state.database_runtime = runtime
        try:
            yield
        finally:
            dispose_database_runtime(runtime)

    app = FastAPI(title="Pitagoras Linguistic Data Platform API", lifespan=lifespan)
    app.state.settings = app_settings
    app.include_router(health_router)
    app.include_router(documents_router)
    return app
