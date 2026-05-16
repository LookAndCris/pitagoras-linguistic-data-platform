from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from packages.core.db import DatabaseRuntime, get_session
from packages.core.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_database_runtime(request: Request) -> DatabaseRuntime:
    return request.app.state.database_runtime


def get_db_session(request: Request) -> Generator[Session, None, None]:
    runtime = get_database_runtime(request)
    yield from get_session(runtime.session_factory)
