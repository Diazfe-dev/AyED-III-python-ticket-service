"""Database engine, per-request session and schema management."""

from typing import Any

import click
from flask import Flask, current_app, g
from flask.cli import with_appcontext
from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import IN_MEMORY_DATABASE_URL
from app.domain.base import Base

EXTENSION_KEY = "sqlalchemy"
SESSION_KEY = "db_session"


def init_app(app: Flask) -> None:
    """Create the engine and session factory of this app instance."""
    engine = _create_engine(app.config["DATABASE_URL"])
    app.extensions[EXTENSION_KEY] = {
        "engine": engine,
        "session_factory": sessionmaker(bind=engine),
    }
    app.teardown_appcontext(_close_session)
    app.cli.add_command(init_db_command)


def create_schema(engine: Engine, metadata: MetaData) -> None:
    """Create the missing tables of the metadata without touching existing data."""
    metadata.create_all(engine)


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Create every table of the domain model that does not exist yet."""
    create_schema(get_engine(), Base.metadata)
    click.echo("Database initialized.")


def get_engine() -> Engine:
    """Return the engine of the current app."""
    return current_app.extensions[EXTENSION_KEY]["engine"]


def get_session() -> Session:
    """Return the session of the current request, creating it on first use."""
    if SESSION_KEY not in g:
        setattr(g, SESSION_KEY, current_app.extensions[EXTENSION_KEY]["session_factory"]())
    return getattr(g, SESSION_KEY)


def _close_session(exc: BaseException | None) -> None:
    """Discard pending changes on failure and always close; committing is the service's job."""
    session: Session | None = g.pop(SESSION_KEY, None)
    if session is None:
        return
    if exc is not None:
        session.rollback()
    session.close()


def _create_engine(url: str) -> Engine:
    engine = _build_engine(url)
    event.listen(engine, "connect", _enable_foreign_keys)
    return engine


def _build_engine(url: str) -> Engine:
    if url == IN_MEMORY_DATABASE_URL:
        return create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    return create_engine(url)


def _enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
