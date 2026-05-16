from collections.abc import Generator
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from packages.core.settings import Settings


@dataclass
class DatabaseRuntime:
    engine: Engine
    session_factory: sessionmaker[Session]


def create_database_runtime(settings: Settings) -> DatabaseRuntime:
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    return DatabaseRuntime(engine=engine, session_factory=session_factory)


def dispose_database_runtime(runtime: DatabaseRuntime) -> None:
    runtime.engine.dispose()


def create_engine_from_settings(settings: Settings) -> Engine:
    database_url = settings.resolved_database_url
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

    engine_kwargs: dict[str, object] = {
        "future": True,
        "connect_args": connect_args,
    }

    if not database_url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "pool_recycle": settings.db_pool_recycle_seconds,
            }
        )

    return create_engine(database_url, **engine_kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
