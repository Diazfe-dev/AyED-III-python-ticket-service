from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner

from app import create_app
from app.db import get_engine


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
