import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.milestone import Milestone
from app.domain.state_change import StateChange
from app.domain.ticket import Ticket, ticket_products
from app.domain.users import User
from tests.conftest import (
    LoginAs,
    MakeCategory,
    MakeProduct,
    MakeProductType,
    MakeTicket,
    MakeUser,
)

TABLES = (Ticket, ticket_products, Milestone, StateChange)


def snapshot(db_session: Session) -> list[int]:
    db_session.expire_all()
    return [db_session.scalar(select(func.count()).select_from(table)) or 0 for table in TABLES]


# (method, path, body) of the write requests an admin makes: the role wins over `404` and
# `invalid_client`.
ADMIN_PRECEDENCE_REQUESTS = [
    ("POST", "/tickets", {"client_id": 9999, "first_message": "Hola"}),
    ("POST", "/tickets/9999/close", None),
    ("POST", "/tickets/9999/reopen", None),
    ("DELETE", "/tickets/9999/products/1", None),
]

# (method, path, body) of the endpoints of `/tickets`, with a ticket that exists. A whole-string
# `{name}` in a body is replaced by that id (an integer); in a path, by `str.format`.
WRITE_ENDPOINTS = [
    ("POST", "/tickets", {"client_id": "{ana}", "first_message": "Hola"}),
    ("POST", "/tickets/{ticket}/close", None),
    ("POST", "/tickets/{ticket}/reopen", None),
    ("POST", "/tickets/{ticket}/products", {"product_ids": ["{xps}"]}),
    ("DELETE", "/tickets/{ticket}/products/{xps}", None),
    ("POST", "/tickets/{ticket}/milestones", {"content": "Hola"}),
]
READ_ENDPOINTS = [
    ("GET", "/tickets", None),
    ("GET", "/tickets/{ticket}", None),
    ("GET", "/tickets/{ticket}/milestones", None),
]

# The endpoints that work on one ticket, for the cases about its visibility.
TICKET_ENDPOINTS = [
    ("GET", "/tickets/{ticket}", None),
    ("POST", "/tickets/{ticket}/close", None),
    ("POST", "/tickets/{ticket}/reopen", None),
    ("POST", "/tickets/{ticket}/products", {"product_ids": ["{xps}"]}),
    ("DELETE", "/tickets/{ticket}/products/{xps}", None),
    ("POST", "/tickets/{ticket}/milestones", {"content": "Hola"}),
    ("GET", "/tickets/{ticket}/milestones", None),
]

WRITE_ENDPOINT_IDS = [f"{method} {path}" for method, path, _ in WRITE_ENDPOINTS]
TICKET_ENDPOINT_IDS = [f"{method} {path}" for method, path, _ in TICKET_ENDPOINTS]


@pytest.fixture
def world(
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
) -> SimpleNamespace:
    """`ana` and `beto` (clients), `raul` and `rosa` (representatives) and the ticket of
    `ana` and `raul` with the product `xps`."""
    ana = make_user("Client", name="Ana")
    beto = make_user("Client", name="Beto")
    raul = make_user("Representative", name="Raul")
    rosa = make_user("Representative", name="Rosa")
    xps = make_product(make_product_type(make_category("Hardware"), "Notebook"), "XPS 13")
    ticket = make_ticket(ana, raul, [xps])
    return SimpleNamespace(ana=ana, beto=beto, raul=raul, rosa=rosa, xps=xps, ticket=ticket)


def resolve(value: Any, ids: dict[str, int]) -> Any:
    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
        return ids[value[1:-1]]
    if isinstance(value, dict):
        return {key: resolve(item, ids) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, ids) for item in value]
    return value


def call(
    client: FlaskClient, endpoint: tuple[str, str, Any], world: SimpleNamespace, **overrides: Any
) -> Any:
    method, path, body = endpoint
    ids = {
        "ticket": world.ticket.id,
        "xps": world.xps.id,
        "ana": world.ana.id,
    } | overrides
    return client.open(path.format(**ids), method=method, json=resolve(body, ids))


@pytest.mark.parametrize("endpoint", WRITE_ENDPOINTS, ids=WRITE_ENDPOINT_IDS)
def test_admin_cannot_use_any_ticket_write_endpoint(
    endpoint: tuple[str, str, Any],
    admin_client: FlaskClient,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-TKT-32 · TC-TKT-32b"""
    before = snapshot(db_session)

    response = call(admin_client, endpoint, world)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert snapshot(db_session) == before


@pytest.mark.parametrize("request_", ADMIN_PRECEDENCE_REQUESTS)
def test_admin_forbidden_wins_over_not_found_and_invalid_body(
    request_: tuple[str, str, Any], admin_client: FlaskClient
) -> None:
    """SPEC-TKT-32 · TC-TKT-32c"""
    method, path, body = request_

    response = admin_client.open(path, method=method, json=body)

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


def test_admin_reads_any_ticket_and_gets_not_found_for_a_missing_one(
    client: FlaskClient, login_as: LoginAs, admin: User, world: SimpleNamespace
) -> None:
    """SPEC-TKT-34 · TC-TKT-34c"""
    login_as(client, world.ana)
    expected = client.get(f"/tickets/{world.ticket.id}")
    login_as(client, admin)

    found = client.get(f"/tickets/{world.ticket.id}")
    missing = client.get("/tickets/9999")

    assert found.status_code == 200
    assert found.get_json() == expected.get_json()
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "ticket_not_found"}


@pytest.mark.parametrize("endpoint", TICKET_ENDPOINTS, ids=TICKET_ENDPOINT_IDS)
def test_another_client_gets_not_found_on_every_ticket_endpoint(
    endpoint: tuple[str, str, Any],
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-TKT-19 · TC-TKT-19c"""
    login_as(client, world.beto)
    before = snapshot(db_session)

    response = call(client, endpoint, world)

    assert response.status_code == 404
    assert response.get_json() == {"error": "ticket_not_found"}
    assert snapshot(db_session) == before


def test_a_foreign_ticket_answers_exactly_like_a_missing_one(
    client: FlaskClient, login_as: LoginAs, world: SimpleNamespace
) -> None:
    """SPEC-TKT-19 · TC-TKT-19d"""
    login_as(client, world.beto)

    foreign = client.get(f"/tickets/{world.ticket.id}")
    missing = client.get("/tickets/9999")

    assert foreign.status_code == missing.status_code == 404
    assert foreign.get_json() == missing.get_json()


@pytest.mark.parametrize(
    "endpoint",
    [
        ("GET", "/tickets/{ticket}", None),
        ("POST", "/tickets/{ticket}/close", None),
        ("POST", "/tickets/{ticket}/reopen", None),
        ("POST", "/tickets/{ticket}/products", {"product_ids": ["{xps}"]}),
        ("DELETE", "/tickets/{ticket}/products/{xps}", None),
    ],
    ids=["GET", "close", "reopen", "add products", "remove product"],
)
def test_a_client_gets_not_found_for_an_out_of_range_ticket_id(
    endpoint: tuple[str, str, Any],
    client: FlaskClient,
    login_as: LoginAs,
    world: SimpleNamespace,
) -> None:
    """SPEC-TKT-19 · TC-TKT-19e"""
    login_as(client, world.ana)

    response = call(client, endpoint, world, ticket=2**63)

    assert response.status_code == 404
    assert response.get_json() == {"error": "ticket_not_found"}


@pytest.mark.parametrize("endpoint", TICKET_ENDPOINTS, ids=TICKET_ENDPOINT_IDS)
def test_another_representative_gets_not_found_on_every_ticket_endpoint(
    endpoint: tuple[str, str, Any],
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-TKT-20 · TC-TKT-20c"""
    login_as(client, world.rosa)
    before = snapshot(db_session)

    response = call(client, endpoint, world)

    assert response.status_code == 404
    assert response.get_json() == {"error": "ticket_not_found"}
    assert snapshot(db_session) == before


@pytest.mark.parametrize("who", ["ana", "raul"])
@pytest.mark.parametrize("endpoint", TICKET_ENDPOINTS, ids=TICKET_ENDPOINT_IDS)
def test_a_missing_ticket_is_not_found_on_every_ticket_endpoint(
    who: str,
    endpoint: tuple[str, str, Any],
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-TKT-30 · TC-TKT-30c"""
    login_as(client, getattr(world, who))
    before = snapshot(db_session)

    response = call(client, endpoint, world, ticket=9999)

    assert response.status_code == 404
    assert response.get_json() == {"error": "ticket_not_found"}
    assert snapshot(db_session) == before


@pytest.mark.parametrize("ticket_id", [2**63, 10**19 + 1])
@pytest.mark.parametrize("endpoint", TICKET_ENDPOINTS, ids=TICKET_ENDPOINT_IDS)
def test_an_out_of_range_ticket_id_is_not_found_on_every_ticket_endpoint(
    ticket_id: int,
    endpoint: tuple[str, str, Any],
    client: FlaskClient,
    login_as: LoginAs,
    world: SimpleNamespace,
) -> None:
    """SPEC-TKT-30 · TC-TKT-30d"""
    login_as(client, world.raul)

    response = call(client, endpoint, world, ticket=ticket_id)

    assert response.status_code == 404
    assert response.get_json() == {"error": "ticket_not_found"}


@pytest.mark.parametrize("who", ["raul", "ana", "rosa", "missing", "out_of_range"])
def test_a_malformed_product_ids_is_the_same_bad_request_for_every_ticket(
    who: str, client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-TKT-24 · TC-TKT-24i"""
    ticket_id = {"missing": 9999, "out_of_range": 2**63}.get(who, world.ticket.id)
    login_as(client, world.raul if who in ("missing", "out_of_range") else getattr(world, who))
    before = snapshot(db_session)

    response = client.post(f"/tickets/{ticket_id}/products", json={"product_ids": "abc"})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"product_ids": "invalid"},
    }
    assert snapshot(db_session) == before


def test_admin_gets_a_bad_request_for_an_invalid_creation_body_and_forbidden_for_a_valid_one(
    admin_client: FlaskClient, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-TKT-32 · TC-TKT-32g"""
    before = snapshot(db_session)

    invalid = admin_client.post("/tickets", json={"first_message": ""})
    valid = admin_client.post("/tickets", json={"client_id": world.ana.id, "first_message": "Hola"})

    assert invalid.status_code == 400
    assert invalid.get_json() == {
        "error": "validation_error",
        "fields": {"client_id": "required", "first_message": "required"},
    }
    assert valid.status_code == 403
    assert valid.get_json() == {"error": "forbidden"}
    assert snapshot(db_session) == before


@pytest.mark.parametrize("target", ["missing", "mine"])
def test_admin_gets_a_bad_request_for_a_malformed_product_ids(
    target: str, admin_client: FlaskClient, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-TKT-24 · TC-TKT-24l"""
    ticket_id, product_ids = (9999, "abc") if target == "missing" else (world.ticket.id, [])
    before = snapshot(db_session)

    response = admin_client.post(
        f"/tickets/{ticket_id}/products", json={"product_ids": product_ids}
    )

    assert response.status_code == 400
    assert response.get_json()["fields"]["product_ids"] == "invalid"
    assert response.get_json()["error"] == "validation_error"
    assert snapshot(db_session) == before


PATH_PARAMETER = re.compile(r"<[^>]+>|{[^}]+}")
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
OPENAPI_CONTRACT = Path(__file__).parents[3] / "docs" / "openapi.json"


def normalized(path: str) -> str:
    return PATH_PARAMETER.sub("{}", path)


def test_the_endpoint_matrix_lists_every_ticket_route_of_the_app(app: Flask) -> None:
    """SPEC-TKT-32 · TC-TKT-32d"""
    routes = {
        (method, normalized(rule.rule))
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/tickets")
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }
    listed = {(method, normalized(path)) for method, path, _ in WRITE_ENDPOINTS + READ_ENDPOINTS}

    assert len(routes) == 9
    assert routes == listed


def test_every_ticket_operation_documents_its_forbidden_with_ticket_forbidden() -> None:
    """SPEC-TKT-27 · TC-TKT-27e"""
    contract = json.loads(OPENAPI_CONTRACT.read_text(encoding="utf-8"))
    operations = [
        (path, method, operation)
        for path, item in contract["paths"].items()
        if path.startswith("/tickets")
        for method, operation in item.items()
        if method in HTTP_METHODS
    ]
    ticket_forbidden = contract["components"]["responses"]["TicketForbidden"]
    error_schema = ticket_forbidden["content"]["application/json"]

    assert len(operations) == 9
    for _, _, operation in operations:
        assert operation["responses"]["403"] == {"$ref": "#/components/responses/TicketForbidden"}
    assert error_schema["schema"] == {"$ref": "#/components/schemas/Error"}
    assert error_schema["example"] == {"error": "forbidden"}
