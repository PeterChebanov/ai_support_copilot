from collections.abc import Generator

from sqlalchemy.orm import Session

from api.config import settings
from db.session import get_session_factory

_session_factory = get_session_factory(settings.database_url)


def get_db() -> Generator[Session, None, None]:
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()


def get_settings():
    return settings
