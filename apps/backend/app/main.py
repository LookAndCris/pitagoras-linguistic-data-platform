from fastapi import FastAPI

from apps.backend.app.api.routes.documents import router as documents_router
from apps.backend.app.api.routes.health import router as health_router
from packages.core.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Pitagoras Linguistic Data Platform API")
    app.state.settings = settings or Settings()
    app.include_router(health_router)
    app.include_router(documents_router)
    return app


app = create_app()
