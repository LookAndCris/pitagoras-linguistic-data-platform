import os
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from docker.errors import DockerException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from apps.backend.app.main import create_app
from packages.core.settings import Settings


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path}"


def _preserve_pitagoras_env() -> tuple[dict[str, str], list[str]]:
    snapshot = {key: value for key, value in os.environ.items() if key.startswith("PITAGORAS_")}
    current_keys = [key for key in os.environ if key.startswith("PITAGORAS_")]
    return snapshot, current_keys


@pytest.fixture
def alembic_upgrade() -> Callable[[str, str], None]:
    def _upgrade(database_url: str, revision: str = "head") -> None:
        snapshot, _ = _preserve_pitagoras_env()
        alembic_cfg = Config("apps/backend/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        try:
            command.upgrade(alembic_cfg, revision)
        finally:
            current_keys = [key for key in os.environ if key.startswith("PITAGORAS_")]
            for key in current_keys:
                os.environ.pop(key, None)
            os.environ.update(snapshot)

    return _upgrade


@pytest.fixture
def sqlite_database_url(tmp_path: Path) -> str:
    return _sqlite_url(tmp_path / "integration.sqlite")


@pytest.fixture
def migrated_sqlite_database_url(
    sqlite_database_url: str,
    alembic_upgrade: Callable[[str, str], None],
) -> str:
    alembic_upgrade(sqlite_database_url)
    return sqlite_database_url


@pytest.fixture
def app_client(migrated_sqlite_database_url: str) -> Generator[TestClient, None, None]:
    app = create_app(Settings(database_url=migrated_sqlite_database_url))
    with TestClient(app) as client:
        yield client


@pytest.fixture
def postgres_database_url() -> Generator[str, None, None]:
    pytest.importorskip("psycopg", exc_type=ImportError)
    postgres_module = pytest.importorskip("testcontainers.postgres")
    try:
        container = postgres_module.PostgresContainer("postgres:16-alpine")
    except DockerException as exc:
        pytest.skip(f"Docker daemon unavailable for integration test: {exc}")

    try:
        container.start()
    except DockerException as exc:
        pytest.skip(f"Docker/PostgreSQL container unavailable for integration test: {exc}")

    try:
        yield container.get_connection_url().replace("+psycopg2", "+psycopg")
    finally:
        container.stop()


@pytest.fixture
def migrated_postgres_database_url(
    postgres_database_url: str,
    alembic_upgrade: Callable[[str, str], None],
) -> str:
    alembic_upgrade(postgres_database_url)
    return postgres_database_url


@pytest.fixture
def postgres_engine(postgres_database_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(postgres_database_url)
    try:
        yield engine
    finally:
        engine.dispose()
