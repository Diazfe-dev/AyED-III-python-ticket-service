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

ADMIN_ONLY_ENDPOINTS = [
    ("POST", "/users"),
    ("PATCH", "/users/1"),
    ("POST", "/users/1/deactivate"),
    ("GET", "/representatives"),
]
CLIENT_FORBIDDEN_ENDPOINTS = [*ADMIN_ONLY_ENDPOINTS, ("GET", "/clients")]


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
def test_representatives_listing_returns_only_representatives(
    admin_client: FlaskClient,
) -> None:
    """SPEC-USR-12 · TC-USR-12c"""
    response = admin_client.get("/representatives")

    assert response.status_code == 200
    users = response.get_json()
    assert users
    assert {user["role"] for user in users} == {"Representative"}


USER_KEYS = {"id", "name", "email", "role", "preferred_channel", "is_active"}


@pytest.fixture
def rosa(make_user: MakeUser) -> User:
    return make_user(role="Representative", name="Rosa", email="rosa@x.com")


@pytest.fixture
def rosa_client(client: FlaskClient, rosa: User, login_as: LoginAs) -> FlaskClient:
    login_as(client, rosa)
    return client


@pytest.fixture
def reference_users(make_user: MakeUser, rosa: User) -> None:
    """Created out of name order on purpose, so the listings cannot pass by sorting on id."""
    make_user(role="Client", name="ana", email="ana@x.com")
    make_user(role="Client", name="Beto", email="beto@x.com", is_active=False)
    make_user(role="Client", name="Ana", email="otra@x.com")
    make_user(role="Client", name="Raúl", email="raul@mail.com")
    make_user(role="Representative", name="Zoe", email="zoe@x.com", is_active=False)


def names(response: Any) -> list[str]:
    assert response.status_code == 200
    return [user["name"] for user in response.get_json()]


@pytest.mark.usefixtures("reference_users")
def test_admin_lists_users_of_every_role_and_state(admin_client: FlaskClient) -> None:
    """SPEC-USR-31 · TC-USR-31c"""
    response = admin_client.get("/users")

    assert response.status_code == 200
    users = response.get_json()
    assert {user["role"] for user in users} == {"Admin", "Representative", "Client"}
    assert {user["is_active"] for user in users} == {True, False}
    assert all(set(user) == USER_KEYS for user in users)


@pytest.mark.usefixtures("reference_users")
@pytest.mark.parametrize("path", ["/users", "/clients", "/representatives"])
def test_user_listings_show_role_and_state(admin_client: FlaskClient, path: str) -> None:
    """SPEC-USR-36 · TC-USR-36a"""
    users = admin_client.get(path).get_json()

    assert all("role" in user for user in users)
    assert {user["is_active"] for user in users} == {True, False}


@pytest.mark.usefixtures("reference_users")
def test_user_listings_search_by_name_or_email(admin_client: FlaskClient) -> None:
    """SPEC-USR-43 · TC-USR-43c"""
    assert names(admin_client.get("/users?q=ana")) == ["ana", "Ana"]
    assert names(admin_client.get("/clients?q=ana")) == ["ana", "Ana"]
    assert names(admin_client.get("/representatives?q=ros")) == ["Rosa"]
    assert names(admin_client.get("/users?q=MAIL.com")) == ["Raúl"]


@pytest.mark.usefixtures("reference_users")
@pytest.mark.parametrize("query", ["?q=", "?q=%20%20"])
def test_blank_search_text_lists_every_user(admin_client: FlaskClient, query: str) -> None:
    """SPEC-USR-43 · TC-USR-43e"""
    assert names(admin_client.get(f"/users{query}")) == names(admin_client.get("/users"))


@pytest.mark.usefixtures("reference_users")
def test_user_listings_filter_by_state(admin_client: FlaskClient) -> None:
    """SPEC-USR-44 · TC-USR-44c"""
    assert names(admin_client.get("/users?is_active=false")) == ["Beto", "Zoe"]
    assert names(admin_client.get("/clients?is_active=true")) == ["ana", "Ana", "Raúl"]
    assert names(admin_client.get("/representatives?is_active=false")) == ["Zoe"]


@pytest.mark.parametrize(
    "path", ["/users?is_active=yes", "/clients?is_active=", "/representatives?is_active=1"]
)
def test_user_listings_reject_an_invalid_state_filter(admin_client: FlaskClient, path: str) -> None:
    """SPEC-USR-45 · TC-USR-45c"""
    response = admin_client.get(path)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"is_active": "invalid"},
    }


@pytest.mark.usefixtures("reference_users")
def test_user_listings_return_a_page_when_asked(admin_client: FlaskClient) -> None:
    """SPEC-USR-47 · TC-USR-47b"""
    users = admin_client.get("/users?page=2&page_size=2").get_json()
    clients = admin_client.get("/clients?page_size=3").get_json()
    representatives = admin_client.get("/representatives?page=1").get_json()

    assert [(users["page"], users["page_size"], users["total"])] == [(2, 2, 7)]
    assert [user["name"] for user in users["items"]] == ["Beto", "Raúl"]
    assert [(clients["page"], clients["page_size"], clients["total"])] == [(1, 3, 4)]
    assert len(clients["items"]) == 3
    assert [(representatives["page"], representatives["page_size"])] == [(1, 20)]
    assert representatives["total"] == 2


@pytest.mark.parametrize(
    ("path", "fields"),
    [
        ("/users?page=0", {"page": "invalid"}),
        ("/users?page_size=101", {"page_size": "invalid"}),
        ("/clients?page=abc&page_size=0", {"page": "invalid", "page_size": "invalid"}),
    ],
)
def test_user_listings_reject_invalid_paging(
    admin_client: FlaskClient, path: str, fields: dict[str, str]
) -> None:
    """SPEC-USR-47 · TC-USR-47d"""
    response = admin_client.get(path)

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": fields}


@pytest.mark.usefixtures("reference_users")
def test_user_listings_order_by_name_without_case_then_id(admin_client: FlaskClient) -> None:
    """SPEC-USR-48 · TC-USR-48c"""
    everyone = ["ana", "Ana", "Beto", "Raúl", "Rosa", "Test User", "Zoe"]
    first = admin_client.get("/users?page=1&page_size=2").get_json()["items"]
    second = admin_client.get("/users?page=2&page_size=2").get_json()["items"]

    assert names(admin_client.get("/clients")) == ["ana", "Ana", "Beto", "Raúl"]
    assert names(admin_client.get("/representatives")) == ["Rosa", "Zoe"]
    assert names(admin_client.get("/users")) == everyone
    assert [user["name"] for user in first + second] == everyone[:4]
    assert len({user["id"] for user in first + second}) == 4


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY_ENDPOINTS)
def test_representative_cannot_manage_users(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, method: str, path: str
) -> None:
    """SPEC-USR-18 · TC-USR-18b"""
    login_as(client, make_user(role="Representative"))

    response = client.open(path, method=method, json=NEW_USER)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


@pytest.mark.parametrize(("method", "path"), CLIENT_FORBIDDEN_ENDPOINTS)
def test_client_cannot_manage_users(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, method: str, path: str
) -> None:
    """SPEC-USR-18 · TC-USR-18c"""
    login_as(client, make_user(role="Client"))

    response = client.open(path, method=method, json=NEW_USER)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


@pytest.mark.usefixtures("reference_users")
def test_representative_lists_the_active_clients(
    rosa_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-USR-32 · TC-USR-32b"""
    response = rosa_client.get("/clients")

    active_ids = db_session.scalars(
        select(User.id).where(User.role == "Client", User.is_active.is_(True))
    ).all()
    assert response.status_code == 200
    assert len(active_ids) == 3
    assert {client["id"] for client in response.get_json()} == set(active_ids)


@pytest.mark.usefixtures("reference_users")
def test_representative_sees_only_id_and_name_of_each_client(rosa_client: FlaskClient) -> None:
    """SPEC-USR-33 · TC-USR-33a"""
    clients = rosa_client.get("/clients").get_json()

    assert clients
    assert all(set(client) == {"id", "name"} for client in clients)


@pytest.mark.usefixtures("reference_users")
def test_representative_page_of_clients_has_only_id_and_name(rosa_client: FlaskClient) -> None:
    """SPEC-USR-33 · TC-USR-33b"""
    page = rosa_client.get("/clients?page=1&page_size=2").get_json()

    assert len(page["items"]) == 2
    assert all(set(client) == {"id", "name"} for client in page["items"])


@pytest.mark.usefixtures("one_user_per_role")
def test_admin_clients_listing_returns_only_clients_in_full(admin_client: FlaskClient) -> None:
    """SPEC-USR-34 · TC-USR-34c"""
    response = admin_client.get("/clients")

    assert response.status_code == 200
    users = response.get_json()
    assert users
    assert {user["role"] for user in users} == {"Client"}
    assert all(set(user) == USER_KEYS for user in users)


@pytest.mark.parametrize(
    ("role", "path"),
    [
        ("Client", "/clients"),
        ("Client", "/users"),
        ("Client", "/representatives"),
        ("Representative", "/users"),
        ("Representative", "/representatives"),
    ],
)
def test_listings_are_forbidden_to_the_roles_without_access(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, role: str, path: str
) -> None:
    """SPEC-USR-35 · TC-USR-35b"""
    login_as(client, make_user(role=role))

    response = client.get(path)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


@pytest.mark.parametrize("query", ["?page=0", "?is_active=yes", "?page_size=101&is_active=1"])
def test_client_gets_forbidden_before_the_query_format_is_checked(
    client: FlaskClient, make_user: MakeUser, login_as: LoginAs, query: str
) -> None:
    """SPEC-USR-35 · TC-USR-35c"""
    login_as(client, make_user(role="Client"))

    response = client.get(f"/clients{query}")

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


@pytest.mark.usefixtures("reference_users")
def test_representative_searches_clients_by_name_only(rosa_client: FlaskClient) -> None:
    """SPEC-USR-46 · TC-USR-46b"""
    assert names(rosa_client.get("/clients?q=OTRA")) == []
    assert names(rosa_client.get("/clients?q=ana")) == ["ana", "Ana"]
    assert names(rosa_client.get("/clients?q=beto")) == []


@pytest.mark.usefixtures("reference_users")
def test_representative_page_of_clients_counts_only_active_ones(rosa_client: FlaskClient) -> None:
    """SPEC-USR-47 · TC-USR-47c"""
    page = rosa_client.get("/clients?page=1&page_size=1").get_json()

    assert page["items"] == [{"id": page["items"][0]["id"], "name": "ana"}]
    assert (page["page"], page["page_size"], page["total"]) == (1, 1, 3)


@pytest.mark.usefixtures("reference_users")
def test_representative_cannot_filter_clients_by_state(rosa_client: FlaskClient) -> None:
    """SPEC-USR-50 · TC-USR-50b"""
    forbidden = rosa_client.get("/clients?is_active=true")
    invalid = rosa_client.get("/clients?is_active=maybe")

    assert forbidden.status_code == 403
    assert forbidden.get_json() == {"error": "forbidden"}
    assert invalid.status_code == 400
    assert invalid.get_json() == {
        "error": "validation_error",
        "fields": {"is_active": "invalid"},
    }


def test_admin_activates_an_inactive_user(
    admin_client: FlaskClient, make_user: MakeUser, db_session: Session
) -> None:
    """SPEC-USR-28 · TC-USR-28c"""
    user = make_user(is_active=False)

    response = admin_client.post(f"/users/{user.id}/activate")

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == USER_KEYS
    assert body["is_active"] is True
    assert stored(db_session, user).is_active is True


def test_reactivated_user_can_log_in_again(
    admin_client: FlaskClient, app: Flask, make_user: MakeUser
) -> None:
    """SPEC-USR-28 · TC-USR-28d"""
    user = make_user(email="back@x.com")
    credentials = {"email": "back@x.com", "password": "password1"}
    admin_client.post(f"/users/{user.id}/deactivate")
    other = app.test_client()

    before = other.post("/login", json=credentials)
    admin_client.post(f"/users/{user.id}/activate")
    after = other.post("/login", json=credentials)

    assert (before.status_code, before.get_json()) == (401, {"error": "invalid_credentials"})
    assert after.status_code == 200


def test_activating_an_active_user_is_not_an_error(
    admin_client: FlaskClient, make_user: MakeUser
) -> None:
    """SPEC-USR-29 · TC-USR-29b"""
    user = make_user()

    response = admin_client.post(f"/users/{user.id}/activate")

    assert response.status_code == 200
    assert response.get_json()["is_active"] is True


@pytest.mark.parametrize("user_id", [9999, 2**63])
def test_activating_an_unknown_user_is_not_found(admin_client: FlaskClient, user_id: int) -> None:
    """SPEC-USR-30 · TC-USR-30b"""
    response = admin_client.post(f"/users/{user_id}/activate")

    assert response.status_code == 404
    assert response.get_json() == {"error": "user_not_found"}


@pytest.mark.parametrize("role", ["Representative", "Client"])
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/users", None),
        ("POST", "/users/{id}/activate", None),
        ("POST", "/users/{id}/password", {"new_password": "newpassword"}),
    ],
    ids=["list", "activate", "password"],
)
def test_new_management_endpoints_are_admin_only(
    client: FlaskClient,
    make_user: MakeUser,
    login_as: LoginAs,
    db_session: Session,
    role: str,
    method: str,
    path: str,
    body: dict[str, str] | None,
) -> None:
    """SPEC-USR-18 · TC-USR-18e"""
    target = make_user(is_active=False)
    password_hash = target.password_hash
    login_as(client, make_user(role=role))

    response = client.open(path.format(id=target.id), method=method, json=body)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    reloaded = stored(db_session, target)
    assert (reloaded.is_active, reloaded.password_hash) == (False, password_hash)


def reset_password(client: FlaskClient, user_id: int, body: dict[str, Any]) -> Any:
    return client.post(f"/users/{user_id}/password", json=body)


def test_admin_resets_a_password_and_the_user_logs_in_with_it(
    admin_client: FlaskClient, app: Flask, make_user: MakeUser
) -> None:
    """SPEC-USR-41 · TC-USR-41b"""
    ana = make_user(email="ana@x.com")

    response = reset_password(admin_client, ana.id, {"new_password": "newpassword"})

    assert response.status_code == 204
    new_login = app.test_client().post(
        "/login", json={"email": "ana@x.com", "password": "newpassword"}
    )
    old_login = app.test_client().post(
        "/login", json={"email": "ana@x.com", "password": "password1"}
    )
    assert (new_login.status_code, old_login.status_code) == (200, 401)


@pytest.mark.parametrize("user_id", [9999, 2**63])
def test_resetting_the_password_of_an_unknown_user_is_not_found(
    admin_client: FlaskClient, user_id: int
) -> None:
    """SPEC-USR-42 · TC-USR-42b"""
    response = reset_password(admin_client, user_id, {"new_password": "newpassword"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "user_not_found"}


def test_reset_rejects_a_short_password_and_keeps_the_hash(
    admin_client: FlaskClient, make_user: MakeUser, db_session: Session
) -> None:
    """SPEC-USR-39 · TC-USR-39d"""
    ana = make_user()
    before = ana.password_hash

    response = reset_password(admin_client, ana.id, {"new_password": "short12"})

    assert response.status_code == 400
    assert response.get_json()["fields"]["new_password"] == "too_short"
    assert stored(db_session, ana).password_hash == before


def test_reset_reports_a_missing_password(admin_client: FlaskClient, make_user: MakeUser) -> None:
    """SPEC-USR-40 · TC-USR-40c"""
    response = reset_password(admin_client, make_user().id, {})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"new_password": "required"},
    }


@pytest.mark.parametrize(
    ("value", "reason"), [(None, "required"), (["x"], "invalid")], ids=["null", "list"]
)
def test_reset_treats_null_as_required_and_non_text_as_invalid(
    admin_client: FlaskClient,
    make_user: MakeUser,
    db_session: Session,
    value: Any,
    reason: str,
) -> None:
    """SPEC-USR-40 · TC-USR-40e"""
    ana = make_user()
    before = ana.password_hash

    response = reset_password(admin_client, ana.id, {"new_password": value})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"new_password": reason},
    }
    assert stored(db_session, ana).password_hash == before
