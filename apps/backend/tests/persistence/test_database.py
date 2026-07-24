"""Unit tests for the database infrastructure module.

These tests cover the object wiring (engine/SessionLocal/Base) and the
`get_db()` "always closes the session" contract, both on normal completion
and when the caller raises inside the `with`/generator block. They do not
require a live PostgreSQL connection, since SQLAlchemy engines and sessions
do not open a real connection until a query is actually executed.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

import app.persistence.database as database_module
from app.persistence.database import Base, SessionLocal, engine, get_db


def test_session_local_is_bound_to_the_module_engine() -> None:
    session = SessionLocal()
    try:
        assert isinstance(session, Session)
        assert session.get_bind() is engine
    finally:
        session.close()


def test_base_is_a_usable_declarative_base() -> None:
    assert hasattr(Base, "metadata")
    assert hasattr(Base, "registry")


def test_get_db_yields_a_session() -> None:
    generator = get_db()
    try:
        session = next(generator)
        assert isinstance(session, Session)
    finally:
        generator.close()


def test_get_db_closes_the_session_after_normal_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_session = MagicMock(spec=Session)
    monkeypatch.setattr(database_module, "SessionLocal", lambda: mock_session)

    generator = get_db()
    session = next(generator)
    assert session is mock_session

    with pytest.raises(StopIteration):
        next(generator)

    mock_session.close.assert_called_once()


def test_get_db_closes_the_session_when_the_caller_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_session = MagicMock(spec=Session)
    monkeypatch.setattr(database_module, "SessionLocal", lambda: mock_session)

    generator = get_db()
    next(generator)

    with pytest.raises(RuntimeError, match="boom"):
        generator.throw(RuntimeError("boom"))

    mock_session.close.assert_called_once()
