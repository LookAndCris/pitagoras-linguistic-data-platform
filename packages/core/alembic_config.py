from collections.abc import Callable

DEFAULT_ALEMBIC_URL = "sqlite+pysqlite:///:memory:"


def resolve_alembic_database_url(
    *,
    configured_url: str,
    settings: object | None = None,
    settings_factory: Callable[[], object] | None = None,
) -> str:
    if configured_url and configured_url != DEFAULT_ALEMBIC_URL:
        return configured_url

    resolved_settings = settings if settings is not None else settings_factory() if settings_factory else None

    if resolved_settings is None:
        raise ValueError("settings or settings_factory is required when configured_url uses default placeholder")

    return getattr(resolved_settings, "resolved_database_url")
