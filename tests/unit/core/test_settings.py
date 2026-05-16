import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from pydantic import ValidationError

from packages.core.settings import Settings


@contextmanager
def _env(vars_to_set: dict[str, str], vars_to_clear: list[str]) -> Iterator[None]:
    snapshot = {key: os.environ.get(key) for key in set(vars_to_set) | set(vars_to_clear)}
    try:
        for key in vars_to_clear:
            os.environ.pop(key, None)
        for key, value in vars_to_set.items():
            os.environ[key] = value
        yield
    finally:
        for key, previous in snapshot.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def test_settings_accepts_explicit_database_url() -> None:
    with _env(
        vars_to_set={
            "PITAGORAS_DATABASE_URL": "sqlite+pysqlite:///tmp/test.sqlite",
        },
        vars_to_clear=[
            "PITAGORAS_DB_HOST",
            "PITAGORAS_DB_PORT",
            "PITAGORAS_DB_NAME",
            "PITAGORAS_DB_USER",
            "PITAGORAS_DB_PASSWORD",
        ],
    ):
        settings = Settings()

    assert settings.resolved_database_url == "sqlite+pysqlite:///tmp/test.sqlite"
    assert settings.db_sslmode == "require"
    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 10


def test_settings_builds_postgres_url_from_split_env_contract() -> None:
    with _env(
        vars_to_set={
            "PITAGORAS_DB_HOST": "db.example.internal",
            "PITAGORAS_DB_PORT": "5433",
            "PITAGORAS_DB_NAME": "pitagoras",
            "PITAGORAS_DB_USER": "pitagoras_app",
            "PITAGORAS_DB_PASSWORD": "secret",
            "PITAGORAS_DB_SSLMODE": "verify-full",
        },
        vars_to_clear=["PITAGORAS_DATABASE_URL"],
    ):
        settings = Settings()

    assert (
        settings.resolved_database_url
        == "postgresql+psycopg://pitagoras_app:secret@db.example.internal:5433/pitagoras?sslmode=verify-full"
    )


def test_settings_rejects_mixed_database_url_and_split_env_contract() -> None:
    with _env(
        vars_to_set={
            "PITAGORAS_DATABASE_URL": "postgresql+psycopg://user:pass@db:5432/app",
            "PITAGORAS_DB_HOST": "db",
            "PITAGORAS_DB_NAME": "app",
            "PITAGORAS_DB_USER": "user",
            "PITAGORAS_DB_PASSWORD": "pass",
        },
        vars_to_clear=["PITAGORAS_DB_PORT"],
    ):
        with pytest.raises(ValidationError, match=r"either database_url or full PITAGORAS_DB_\* contract"):
            Settings()


def test_settings_rejects_partial_split_env_contract() -> None:
    with _env(
        vars_to_set={
            "PITAGORAS_DB_HOST": "db",
            "PITAGORAS_DB_NAME": "app",
            "PITAGORAS_DB_USER": "user",
        },
        vars_to_clear=["PITAGORAS_DATABASE_URL", "PITAGORAS_DB_PASSWORD", "PITAGORAS_DB_PORT"],
    ):
        with pytest.raises(ValidationError, match=r"full PITAGORAS_DB_\* contract"):
            Settings()
