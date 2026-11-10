from collections.abc import Callable

import pytest
from flask import Flask
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    func,
    insert,
    inspect,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import create_schema, get_engine, get_session


@pytest.fixture
def sessions_seen(app: Flask) -> list[tuple[Session, Session]]:
    """Register a test-only route that records the sessions each request obtains."""
    seen: list[tuple[Session, Session]] = []

    @app.get("/test/session")
    def use_session() -> str:
        seen.append((get_session(), get_session()))
        return "ok"

    return seen


@pytest.fixture
def session_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record, in order, the rollback and close calls made on any session."""
    calls: list[str] = []
    for name in ("rollback", "close"):
        monkeypatch.setattr(Session, name, _recording(getattr(Session, name), name, calls))
    return calls


def _recording(method: Callable[..., None], name: str, calls: list[str]) -> Callable[..., None]:
    def wrapper(self: Session) -> None:
        calls.append(name)
        method(self)

    return wrapper


@pytest.fixture
def metadata() -> MetaData:
    metadata = MetaData()
    Table("parent", metadata, Column("id", Integer, primary_key=True))
    Table(
        "child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey("parent.id"), nullable=False),
    )
    return metadata


def test_new_connection_enables_foreign_keys(app: Flask) -> None:
    """SPEC-PLT-05 · TC-PLT-05a"""
    with app.app_context(), get_engine().connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

    assert foreign_keys == 1


def test_insert_with_missing_foreign_key_is_rejected(app: Flask, metadata: MetaData) -> None:
    """SPEC-PLT-05 · TC-PLT-05b"""
    with app.app_context(), get_engine().begin() as connection:
        metadata.create_all(connection)
        with pytest.raises(IntegrityError):
            connection.execute(insert(metadata.tables["child"]).values(id=1, parent_id=99))


def test_session_is_reused_within_a_request(
    app: Flask, sessions_seen: list[tuple[Session, Session]]
) -> None:
    """SPEC-PLT-06 · TC-PLT-06a"""
    app.test_client().get("/test/session")

    first_call, second_call = sessions_seen[0]
    assert first_call is second_call


def test_each_request_gets_its_own_session(
    app: Flask, sessions_seen: list[tuple[Session, Session]]
) -> None:
    """SPEC-PLT-06 · TC-PLT-06b"""
    client = app.test_client()
    client.get("/test/session")
    client.get("/test/session")

    (first_request, _), (second_request, _) = sessions_seen
    assert first_request is not second_request


def test_session_is_closed_when_request_ends(
    app: Flask, sessions_seen: list[tuple[Session, Session]], session_calls: list[str]
) -> None:
    """SPEC-PLT-07 · TC-PLT-07a"""
    app.test_client().get("/test/session")

    assert session_calls == ["close"]


def test_unhandled_exception_rolls_back_before_closing(
    app: Flask, metadata: MetaData, session_calls: list[str]
) -> None:
    """SPEC-PLT-08 · TC-PLT-08a"""
    parent = metadata.tables["parent"]
    with app.app_context():
        metadata.create_all(get_engine())

    @app.get("/test/failure")
    def fail_after_add() -> str:
        get_session().execute(insert(parent).values(id=1))
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        app.test_client().get("/test/failure")

    with app.app_context(), get_engine().connect() as connection:
        rows = connection.execute(select(func.count()).select_from(parent)).scalar_one()
    assert session_calls == ["rollback", "close"]
    assert rows == 0


def test_create_schema_creates_metadata_tables(app: Flask, metadata: MetaData) -> None:
    """SPEC-PLT-09 · TC-PLT-09a"""
    with app.app_context():
        engine = get_engine()
        create_schema(engine, metadata)

        tables = set(inspect(engine).get_table_names())

    assert tables == {"parent", "child"}


def test_create_schema_keeps_existing_rows(app: Flask, metadata: MetaData) -> None:
    """SPEC-PLT-09 · TC-PLT-09b"""
    parent = metadata.tables["parent"]
    with app.app_context():
        engine = get_engine()
        create_schema(engine, metadata)
        with engine.begin() as connection:
            connection.execute(insert(parent).values(id=1))

        create_schema(engine, metadata)

        with engine.connect() as connection:
            ids = connection.execute(select(parent.c.id)).scalars().all()
    assert ids == [1]
