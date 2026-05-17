from __future__ import annotations

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from packages.core.alembic_config import resolve_alembic_database_url
from packages.core.schema import Base
from packages.core.settings import Settings

config = context.config
load_dotenv()
target_metadata = Base.metadata


def _resolved_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url")
    return resolve_alembic_database_url(configured_url=configured_url, settings_factory=Settings)


def run_migrations_offline() -> None:
    url = _resolved_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    config.set_main_option("sqlalchemy.url", _resolved_url())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
