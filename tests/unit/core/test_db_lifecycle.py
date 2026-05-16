import importlib
import sys
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.requests import Request

from apps.backend.app.main import create_app
from packages.core.db import DatabaseRuntime
from packages.core.dependencies import get_db_session
from packages.core.settings import Settings


@dataclass
class _FakeSession:
    closed: bool = False

    def close(self) -> None:
        self.closed = True


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> _FakeSession:
        self.calls += 1
        return _FakeSession()


class _FakeEngine:
    disposed = False

    def dispose(self) -> None:
        self.disposed = True


def _build_request(app: FastAPI) -> Request:
    return Request(
        {
            "type": "http",
            "app": app,
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
            "http_version": "1.1",
        }
    )


def test_create_app_initializes_single_runtime_and_disposes_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    created_runtime = DatabaseRuntime(engine=_FakeEngine(), session_factory=_FakeSessionFactory())
    created_calls: list[Settings] = []
    disposed_calls: list[DatabaseRuntime] = []

    def _fake_create_runtime(settings: Settings) -> DatabaseRuntime:
        created_calls.append(settings)
        return created_runtime

    def _fake_dispose_runtime(runtime: DatabaseRuntime) -> None:
        disposed_calls.append(runtime)

    monkeypatch.setattr("apps.backend.app.main.create_database_runtime", _fake_create_runtime)
    monkeypatch.setattr("apps.backend.app.main.dispose_database_runtime", _fake_dispose_runtime)

    app = create_app(Settings(database_url="sqlite+pysqlite:///:memory:"))

    with TestClient(app):
        assert app.state.database_runtime is created_runtime

    assert len(created_calls) == 1
    assert disposed_calls == [created_runtime]


def test_get_db_session_uses_app_scoped_factory_and_closes_per_request_session() -> None:
    app = FastAPI()
    session_factory = _FakeSessionFactory()
    app.state.database_runtime = DatabaseRuntime(engine=_FakeEngine(), session_factory=session_factory)

    first_generator = get_db_session(_build_request(app))
    first_session = next(first_generator)
    assert first_session.closed is False
    with pytest.raises(StopIteration):
        next(first_generator)
    assert first_session.closed is True

    second_generator = get_db_session(_build_request(app))
    second_session = next(second_generator)
    with pytest.raises(StopIteration):
        next(second_generator)

    assert second_session.closed is True
    assert second_session is not first_session
    assert session_factory.calls == 2


def test_create_engine_from_settings_applies_postgres_pool_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.delenv("PITAGORAS_DATABASE_URL", raising=False)

    def _fake_create_engine(url: str, **kwargs: object) -> object:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr("packages.core.db.create_engine", _fake_create_engine)

    settings = Settings(
        db_host="db.internal",
        db_name="pitagoras",
        db_user="pitagoras",
        db_password="secret",
        db_pool_size=7,
        db_max_overflow=13,
        db_pool_recycle_seconds=900,
    )

    from packages.core.db import create_engine_from_settings

    create_engine_from_settings(settings)

    assert captured["url"] == settings.resolved_database_url
    kwargs = captured["kwargs"]
    assert kwargs["pool_size"] == 7
    assert kwargs["max_overflow"] == 13
    assert kwargs["pool_recycle"] == 900


def test_create_app_fails_fast_when_required_db_config_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    env_keys = [
        "PITAGORAS_DATABASE_URL",
        "PITAGORAS_DB_HOST",
        "PITAGORAS_DB_PORT",
        "PITAGORAS_DB_NAME",
        "PITAGORAS_DB_USER",
        "PITAGORAS_DB_PASSWORD",
    ]
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError, match="either database_url or full PITAGORAS_DB_\\* contract"):
        create_app()


def test_importing_main_module_does_not_validate_settings_until_app_factory_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_keys = [
        "PITAGORAS_DATABASE_URL",
        "PITAGORAS_DB_HOST",
        "PITAGORAS_DB_PORT",
        "PITAGORAS_DB_NAME",
        "PITAGORAS_DB_USER",
        "PITAGORAS_DB_PASSWORD",
    ]
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)

    module_name = "apps.backend.app.main"
    sys.modules.pop(module_name, None)

    main_module = importlib.import_module(module_name)

    assert callable(main_module.create_app)


def test_create_app_after_import_still_fails_fast_when_db_contract_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_keys = [
        "PITAGORAS_DATABASE_URL",
        "PITAGORAS_DB_HOST",
        "PITAGORAS_DB_PORT",
        "PITAGORAS_DB_NAME",
        "PITAGORAS_DB_USER",
        "PITAGORAS_DB_PASSWORD",
    ]
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)

    module_name = "apps.backend.app.main"
    sys.modules.pop(module_name, None)
    main_module = importlib.import_module(module_name)

    with pytest.raises(ValidationError, match="either database_url or full PITAGORAS_DB_\\* contract"):
        main_module.create_app()
