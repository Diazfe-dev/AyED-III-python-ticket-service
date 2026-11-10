from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.auth import USER_ID_KEY, login_required
from app.domain.users import User
from tests.conftest import MakeUser

INVALID_CREDENTIALS = {"error": "invalid_credentials"}


@pytest.fixture
def ana(make_user: MakeUser) -> User:
    return make_user(role="Representative", email="ana@x.com", name="Ana")


@pytest.fixture
def protected_route(app: Flask) -> None:
    @app.get("/test/protected")
    @login_required
    def protected() -> dict[str, bool]:
        return {"ok": True}


def session_data(client: FlaskClient) -> dict[str, Any]:
    with client.session_transaction() as session:
        return dict(session)


@pytest.mark.usefixtures("protected_route")
def test_login_with_valid_credentials_starts_a_session(client: FlaskClient, ana: User) -> None:
    """SPEC-USR-14 · TC-USR-14b"""
    response = client.post("/login", json={"email": " ANA@x.com ", "password": "password1"})

    assert response.status_code == 200
    assert response.get_json() == {
        "id": ana.id,
        "name": "Ana",
        "email": "ana@x.com",
        "role": "Representative",
    }
    assert session_data(client)[USER_ID_KEY] == ana.id
    assert client.get("/test/protected").status_code == 200


def test_login_discards_data_of_the_previous_session(client: FlaskClient, ana: User) -> None:
    """SPEC-USR-14 · TC-USR-14c"""
    with client.session_transaction() as session:
        session["stale"] = 1

    client.post("/login", json={"email": "ana@x.com", "password": "password1"})

    assert "stale" not in session_data(client)


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "nobody@x.com", "password": "password1"},
        {"email": "ana@x.com", "password": "wrong-password"},
        {"email": "inactive@x.com", "password": "password1"},
    ],
    ids=["unknown-email", "wrong-password", "inactive-user"],
)
def test_failed_login_gives_the_same_generic_answer(
    client: FlaskClient, ana: User, make_user: MakeUser, credentials: dict[str, str]
) -> None:
    """SPEC-USR-15 · TC-USR-15d"""
    make_user(email="inactive@x.com", is_active=False)

    response = client.post("/login", json=credentials)

    assert response.status_code == 401
    assert response.get_json() == INVALID_CREDENTIALS
    assert USER_ID_KEY not in session_data(client)


@pytest.mark.parametrize(
    "body",
    [None, {}, {"email": "ana@x.com"}],
    ids=["no-body", "empty-object", "missing-password"],
)
def test_login_with_missing_fields_is_an_invalid_credentials_answer(
    client: FlaskClient, ana: User, body: dict[str, str] | None
) -> None:
    """SPEC-USR-15 · TC-USR-15e"""
    response = client.post("/login", json=body)

    assert response.status_code == 401
    assert response.get_json() == INVALID_CREDENTIALS


def log_in(client: FlaskClient) -> None:
    response = client.post("/login", json={"email": "ana@x.com", "password": "password1"})
    assert response.status_code == 200


@pytest.mark.usefixtures("protected_route")
def test_logout_ends_access_to_protected_routes(client: FlaskClient, ana: User) -> None:
    """SPEC-USR-17 · TC-USR-17a"""
    log_in(client)

    response = client.post("/logout")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get("/test/protected").status_code == 401


def test_logout_removes_the_user_from_the_session(client: FlaskClient, ana: User) -> None:
    """SPEC-USR-17 · TC-USR-17b"""
    log_in(client)

    client.post("/logout")

    assert USER_ID_KEY not in session_data(client)
