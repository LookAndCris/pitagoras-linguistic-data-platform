from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.backend.app.main import create_app
from packages.core.settings import Settings


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path}"


def _upgrade_to_head(database_url: str) -> None:
    alembic_cfg = Config("apps/backend/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


def test_liveness_succeeds_when_process_is_running() -> None:
    app = create_app(Settings(database_url="sqlite+pysqlite:///:memory:"))

    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_fails_before_migrations_complete(tmp_path: Path) -> None:
    db_path = tmp_path / "premigration.sqlite"
    app = create_app(Settings(database_url=_sqlite_url(db_path)))

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database schema is not ready"


def test_readiness_succeeds_after_migrations_complete(tmp_path: Path) -> None:
    db_path = tmp_path / "ready.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_and_readiness_succeed_in_same_ready_state(tmp_path: Path) -> None:
    db_path = tmp_path / "ready-state.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok"}


def test_liveness_stays_up_when_database_is_unreachable(tmp_path: Path) -> None:
    unreachable_url = _sqlite_url(tmp_path / "missing" / "nested" / "db.sqlite")
    app = create_app(Settings(database_url=unreachable_url))

    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 503
