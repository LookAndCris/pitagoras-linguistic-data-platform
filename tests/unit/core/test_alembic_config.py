from packages.core.alembic_config import DEFAULT_ALEMBIC_URL, resolve_alembic_database_url


class _StubSettings:
    resolved_database_url = "postgresql+psycopg://app:secret@db.internal:5432/pitagoras?sslmode=require"


def test_resolve_alembic_database_url_keeps_explicit_cli_override() -> None:
    explicit_url = "sqlite+pysqlite:////tmp/test.sqlite"

    resolved = resolve_alembic_database_url(configured_url=explicit_url, settings=_StubSettings())

    assert resolved == explicit_url


def test_resolve_alembic_database_url_uses_settings_when_default_placeholder() -> None:
    resolved = resolve_alembic_database_url(configured_url=DEFAULT_ALEMBIC_URL, settings=_StubSettings())

    assert resolved == _StubSettings.resolved_database_url


def test_resolve_alembic_database_url_keeps_explicit_override_without_building_settings() -> None:
    explicit_url = "sqlite+pysqlite:////tmp/test.sqlite"

    def _explode() -> object:
        raise AssertionError("settings_factory should not be called for explicit URL overrides")

    resolved = resolve_alembic_database_url(
        configured_url=explicit_url,
        settings_factory=_explode,
    )

    assert resolved == explicit_url
