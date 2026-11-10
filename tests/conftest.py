from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy.orm import Session

from app import create_app
from app.db import EXTENSION_KEY, create_schema, get_engine
from app.domain.base import Base


@pytest.fixture
def app() -> Iterator[Flask]:
    app = create_app({"TESTING": True})
    yield app
    with app.app_context():
        get_engine().dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    return app.test_cli_runner()


@pytest.fixture
def schema(app: Flask) -> None:
    """Create every domain table in the in-memory database of the test app."""
    with app.app_context():
        create_schema(get_engine(), Base.metadata)


@pytest.fixture
def db_session(app: Flask, schema: None) -> Iterator[Session]:
    """A session built straight from the factory, without holding an app context open.

    Holding an app context would make the test client reuse it, so every request would
    share this session and skip its own teardown.
    """
    session = app.extensions[EXTENSION_KEY]["session_factory"]()
    yield session
    session.close()
