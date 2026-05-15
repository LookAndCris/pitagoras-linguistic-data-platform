from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from packages.core.db import create_engine_from_settings, create_session_factory, get_session
from packages.core.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db_session(request: Request) -> Generator[Session, None, None]:
    settings = get_settings(request)
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    yield from get_session(session_factory)
