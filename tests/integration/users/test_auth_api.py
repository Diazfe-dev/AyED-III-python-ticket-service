from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash

from app.auth import USER_ID_KEY, login_required
from app.domain.users import User
from tests.conftest import LoginAs, MakeUser

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


@pytest.mark.parametrize(
    "credentials",
    [{"email": 123, "password": "password1"}, {"email": "ana@x.com", "password": ["password1"]}],
    ids=["numeric-email", "list-password"],
)
def test_login_with_non_text_credentials_is_an_invalid_credentials_answer(
    client: FlaskClient, ana: User, credentials: dict[str, Any]
) -> None:
    """SPEC-USR-25 · TC-USR-25f"""
    response = client.post("/login", json=credentials)

    assert response.status_code == 401
    assert response.get_json() == INVALID_CREDENTIALS
    assert USER_ID_KEY not in session_data(client)


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


@pytest.mark.parametrize("role", ["Admin", "Representative", "Client"])
def test_me_returns_only_the_identity_of_the_session_user(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, role: str
) -> None:
    """SPEC-USR-27 · TC-USR-27a"""
    user = make_user(role=role, email="me@x.com", name="Me")
    login_as(client, user)

    response = client.get("/me")

    assert response.status_code == 200
    assert response.get_json() == {
        "id": user.id,
        "name": "Me",
        "email": "me@x.com",
        "role": role,
    }


NEW_PASSWORD = "newpassword"


def change_password(client: FlaskClient, current: Any, new: Any) -> Any:
    return client.post("/me/password", json={"current_password": current, "new_password": new})


def stored_hash(db_session: Session, user: User) -> str:
    db_session.expire_all()
    return db_session.get_one(User, user.id).password_hash


@pytest.fixture
def ana_client(client: FlaskClient, ana: User, login_as: LoginAs) -> FlaskClient:
    login_as(client, ana)
    return client


def test_own_password_change_stores_a_hash_and_keeps_the_session(
    ana_client: FlaskClient, ana: User, db_session: Session, app: Flask
) -> None:
    """SPEC-USR-37 · TC-USR-37b"""
    response = change_password(ana_client, "password1", NEW_PASSWORD)

    assert response.status_code == 204
    saved = stored_hash(db_session, ana)
    assert saved != NEW_PASSWORD
    assert check_password_hash(saved, NEW_PASSWORD)
    new_login = app.test_client().post(
        "/login", json={"email": "ana@x.com", "password": NEW_PASSWORD}
    )
    old_login = app.test_client().post(
        "/login", json={"email": "ana@x.com", "password": "password1"}
    )
    assert (new_login.status_code, old_login.status_code) == (200, 401)
    assert ana_client.get("/me").status_code == 200


def test_wrong_current_password_is_a_400_and_keeps_the_session(
    ana_client: FlaskClient, ana: User, db_session: Session
) -> None:
    """SPEC-USR-38 · TC-USR-38b"""
    before = stored_hash(db_session, ana)

    response = change_password(ana_client, "wrong-pass", NEW_PASSWORD)

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_current_password"}
    assert stored_hash(db_session, ana) == before
    assert ana_client.get("/me").status_code == 200


def test_own_password_change_rejects_a_short_new_password(
    ana_client: FlaskClient, ana: User, db_session: Session
) -> None:
    """SPEC-USR-39 · TC-USR-39d"""
    before = stored_hash(db_session, ana)

    response = change_password(ana_client, "password1", "short12")

    assert response.status_code == 400
    assert response.get_json()["fields"]["new_password"] == "too_short"
    assert stored_hash(db_session, ana) == before


@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({}, {"current_password": "required", "new_password": "required"}),
        ({"current_password": 1, "new_password": NEW_PASSWORD}, {"current_password": "invalid"}),
    ],
    ids=["empty-body", "numeric-current"],
)
def test_own_password_change_reports_missing_and_invalid_fields(
    ana_client: FlaskClient, body: dict[str, Any], fields: dict[str, str]
) -> None:
    """SPEC-USR-40 · TC-USR-40c"""
    response = ana_client.post("/me/password", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": fields}


@pytest.mark.parametrize(
    ("current", "new", "fields"),
    [
        (None, None, {"current_password": "required", "new_password": "required"}),
        ("password1", 12345678, {"new_password": "invalid"}),
    ],
    ids=["null-fields", "numeric-new"],
)
def test_own_password_change_treats_null_as_required_and_non_text_as_invalid(
    ana_client: FlaskClient,
    ana: User,
    db_session: Session,
    current: Any,
    new: Any,
    fields: dict[str, str],
) -> None:
    """SPEC-USR-40 · TC-USR-40e"""
    before = stored_hash(db_session, ana)

    response = change_password(ana_client, current, new)

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": fields}
    assert stored_hash(db_session, ana) == before
