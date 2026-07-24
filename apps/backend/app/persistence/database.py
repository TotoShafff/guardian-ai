"""Database infrastructure for the Guardian AI backend.

Provides the SQLAlchemy `engine`, the `SessionLocal` session factory, the
declarative `Base` class, and a `get_db()` dependency that yields a
request-scoped session and always closes it. This module intentionally
defines no ORM models, no tables, and performs no migrations — see
`docs/ARCHITECTURE.md` Section 12 for the data model and `docs/ROADMAP.md`
for when it is implemented.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

engine: Engine = create_engine(get_settings().database_url)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base class shared by all ORM models (defined in later stages)."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for the duration of a request, always closing it."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
