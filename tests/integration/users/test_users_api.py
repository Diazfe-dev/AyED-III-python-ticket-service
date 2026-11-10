from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash

from app.domain.users import User
from tests.conftest import LoginAs, MakeUser

NEW_USER: dict[str, Any] = {
    "name": "Ana",
    "email": "ana@x.com",
    "role": "Representative",
    "password": "password1",
}

MANAGEMENT_ENDPOINTS = [
    ("POST", "/users"),
    ("PATCH", "/users/1"),
    ("POST", "/users/1/deactivate"),
    ("GET", "/clients"),
    ("GET", "/representatives"),
]


def create_user(client: FlaskClient, **overrides: Any) -> Any:
    return client.post("/users", json=NEW_USER | overrides)


def count_users(db_session: Session) -> int:
    db_session.expire_all()
    return db_session.scalar(select(func.count()).select_from(User)) or 0


def test_admin_creates_an_active_user(admin_client: FlaskClient) -> None:
    """SPEC-USR-01 · TC-USR-01d"""
    response = create_user(admin_client)

    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body["id"], int)
    assert body["role"] == "Representative"
    assert body["is_active"] is True


def test_created_user_exposes_and_stores_no_plain_password(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-USR-02 · TC-USR-02c"""
    body = create_user(admin_client).get_json()

    assert "password" not in body
    assert "password_hash" not in body
    stored = db_session.get(User, body["id"])
    assert stored is not None
    assert stored.password_hash != "password1"
    assert check_password_hash(stored.password_hash, "password1")


def test_create_user_with_taken_email_in_other_case_is_a_conflict(
    admin_client: FlaskClient, make_user: MakeUser
) -> None:
    """SPEC-USR-04 · TC-USR-04d"""
    make_user(email="ana@x.com")

    response = create_user(admin_client, email=" ANA@X.com")

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_email"}


def test_create_user_reports_invalid_fields(admin_client: FlaskClient) -> None:
    """SPEC-USR-05 · TC-USR-05f"""
    response = create_user(admin_client, name=None, email="ana-at-x")

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"name": "required", "email": "invalid"},
    }


def test_create_user_without_channel_gets_mail(admin_client: FlaskClient) -> None:
    """SPEC-USR-06 · TC-USR-06c"""
    response = create_user(admin_client)

    assert response.get_json()["preferred_channel"] == "mail"


def test_create_user_with_short_password_is_rejected(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-USR-19 · TC-USR-19c"""
    users_before = count_users(db_session)

    response = create_user(admin_client, password="passwor")

    assert response.status_code == 400
    assert response.get_json()["fields"]["password"] == "too_short"
    assert count_users(db_session) == users_before


def test_create_user_with_unknown_channel_is_rejected(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-USR-23 · TC-USR-23c"""
    users_before = count_users(db_session)

    response = create_user(admin_client, preferred_channel="sms")

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"preferred_channel": "invalid"}
    assert count_users(db_session) == users_before


def test_create_user_with_non_text_values_is_rejected(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-USR-25 · TC-USR-25d"""
    users_before = count_users(db_session)

    response = create_user(admin_client, name=123, preferred_channel=["mail"])

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"name": "invalid", "preferred_channel": "invalid"},
    }
    assert count_users(db_session) == users_before


def stored(db_session: Session, user: User) -> User:
    """Reload the user from the database, after the requests of the test committed."""
    db_session.expire_all()
    return db_session.get_one(User, user.id)


def test_admin_updates_name_email_and_channel_but_not_role(
    admin_client: FlaskClient, make_user: MakeUser, db_session: Session
) -> None:
    """SPEC-USR-07 · TC-USR-07d"""
    user = make_user(role="Client", email="ana@x.com")
    changes = {
        "name": "Ana María",
        "email": "AnaM@x.com",
        "preferred_channel": "whatsapp",
        "role": "Admin",
    }

    response = admin_client.patch(f"/users/{user.id}", json=changes)

    assert response.status_code == 200
    body = response.get_json()
    assert (body["name"], body["email"], body["preferred_channel"]) == (
        "Ana María",
        "anam@x.com",
        "whatsapp",
    )
    assert body["role"] == "Client"
    assert stored(db_session, user).role == "Client"


def test_update_of_unknown_user_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-USR-26 · TC-USR-26c"""
    response = admin_client.patch("/users/9999", json={"name": "Nobody"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "user_not_found"}


def test_update_to_an_email_of_another_user_is_a_conflict(
    admin_client: FlaskClient, make_user: MakeUser
) -> None:
    """SPEC-USR-08 · TC-USR-08b"""
    ana, bea = make_user(email="ana@x.com"), make_user(email="bea@x.com")

    response = admin_client.patch(f"/users/{ana.id}", json={"email": bea.email})

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_email"}


def test_update_with_empty_name_and_malformed_email_is_rejected(
    admin_client: FlaskClient, make_user: MakeUser, db_session: Session
) -> None:
    """SPEC-USR-22 · TC-USR-22d"""
    user = make_user(email="ana@x.com", name="Ana")

    response = admin_client.patch(f"/users/{user.id}", json={"name": "", "email": "ana-at-x"})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"name": "required", "email": "invalid"},
    }
    reloaded = stored(db_session, user)
    assert (reloaded.name, reloaded.email) == ("Ana", "ana@x.com")


def test_update_with_unknown_channel_is_rejected(
    admin_client: FlaskClient, make_user: MakeUser, db_session: Session
) -> None:
    """SPEC-USR-23 · TC-USR-23d"""
    user = make_user()

    response = admin_client.patch(f"/users/{user.id}", json={"preferred_channel": "sms"})

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"preferred_channel": "invalid"}
    assert stored(db_session, user).preferred_channel == "mail"


def test_update_with_non_text_email_is_rejected(
    admin_client: FlaskClient, make_user: MakeUser, db_session: Session
) -> None:
    """SPEC-USR-25 · TC-USR-25e"""
    user = make_user(email="ana@x.com")

    response = admin_client.patch(f"/users/{user.id}", json={"email": 123})

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"email": "invalid"}
    assert stored(db_session, user).email == "ana@x.com"


def test_admin_deactivates_a_user(admin_client: FlaskClient, make_user: MakeUser) -> None:
    """SPEC-USR-09 · TC-USR-09c"""
    user = make_user()

    response = admin_client.post(f"/users/{user.id}/deactivate")

    assert response.status_code == 200
    assert response.get_json()["is_active"] is False


def test_deactivating_an_unknown_user_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-USR-26 · TC-USR-26d"""
    response = admin_client.post("/users/9999/deactivate")

    assert response.status_code == 404
    assert response.get_json() == {"error": "user_not_found"}


@pytest.mark.parametrize(
    ("method", "path"),
    [("PATCH", f"/users/{2**63}"), ("POST", f"/users/{2**63}/deactivate")],
)
def test_user_id_beyond_sqlite_integers_is_not_found(
    admin_client: FlaskClient, method: str, path: str
) -> None:
    """SPEC-USR-26 · TC-USR-26f"""
    response = admin_client.open(path, method=method, json={"name": "Nobody"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "user_not_found"}


def test_deactivated_user_row_is_kept_with_all_its_data(
    admin_client: FlaskClient, make_user: MakeUser, db_session: Session
) -> None:
    """SPEC-USR-10 · TC-USR-10a"""
    user = make_user(role="Representative", email="rep@x.com", name="Rep")
    password_hash = user.password_hash

    admin_client.post(f"/users/{user.id}/deactivate")

    reloaded = stored(db_session, user)
    assert (reloaded.name, reloaded.email, reloaded.role, reloaded.password_hash) == (
        "Rep",
        "rep@x.com",
        "Representative",
        password_hash,
    )
    assert reloaded.is_active is False


def test_no_user_route_accepts_delete(app: Flask) -> None:
    """SPEC-USR-10 · TC-USR-10c"""
    user_rules = [
        rule
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith(("/users", "/clients", "/representatives"))
    ]

    assert user_rules
    assert all("DELETE" not in rule.methods for rule in user_rules)


def test_admin_cannot_deactivate_itself_through_the_api(
    admin_client: FlaskClient, admin: User
) -> None:
    """SPEC-USR-21 · TC-USR-21b"""
    response = admin_client.post(f"/users/{admin.id}/deactivate")

    assert response.status_code == 409
    assert response.get_json() == {"error": "self_deactivation"}


@pytest.fixture
def one_user_per_role(make_user: MakeUser) -> None:
    for role in ("Representative", "Client"):
        make_user(role=role)


@pytest.mark.usefixtures("one_user_per_role")
def test_clients_listing_returns_only_clients(admin_client: FlaskClient) -> None:
    """SPEC-USR-11 · TC-USR-11c"""
    response = admin_client.get("/clients")

    assert response.status_code == 200
    users = response.get_json()
    assert users
    assert {user["role"] for user in users} == {"Client"}


@pytest.mark.usefixtures("one_user_per_role")
def test_representatives_listing_returns_only_representatives(
    admin_client: FlaskClient,
) -> None:
    """SPEC-USR-12 · TC-USR-12c"""
    response = admin_client.get("/representatives")

    assert response.status_code == 200
    users = response.get_json()
    assert users
    assert {user["role"] for user in users} == {"Representative"}


def test_listing_shows_role_and_state_of_active_and_inactive_users(
    admin_client: FlaskClient, make_user: MakeUser
) -> None:
    """SPEC-USR-13 · TC-USR-13a"""
    make_user(role="Client", email="active@x.com")
    make_user(role="Client", email="inactive@x.com", is_active=False)

    users = admin_client.get("/clients").get_json()

    assert [(user["email"], user["role"], user["is_active"]) for user in users] == [
        ("active@x.com", "Client", True),
        ("inactive@x.com", "Client", False),
    ]


@pytest.mark.parametrize(("method", "path"), MANAGEMENT_ENDPOINTS)
def test_representative_cannot_manage_users(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, method: str, path: str
) -> None:
    """SPEC-USR-18 · TC-USR-18b"""
    login_as(client, make_user(role="Representative"))

    response = client.open(path, method=method, json=NEW_USER)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


@pytest.mark.parametrize(("method", "path"), MANAGEMENT_ENDPOINTS)
def test_client_cannot_manage_users(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, method: str, path: str
) -> None:
    """SPEC-USR-18 · TC-USR-18c"""
    login_as(client, make_user(role="Client"))

    response = client.open(path, method=method, json=NEW_USER)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
