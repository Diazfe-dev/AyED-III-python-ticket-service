from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.controllers.serializers import product_json
from app.domain.milestone import Milestone
from app.domain.products import Product, ProductType
from app.domain.state_change import StateChange
from app.domain.ticket import Ticket, ticket_products
from app.domain.users import Client, Representative
from app.repositories.ticket_repository import SqlAlchemyTicketRepository
from tests.conftest import (
    DEFAULT_TICKET_TIME,
    LoginAs,
    MakeCategory,
    MakeProduct,
    MakeProductType,
    MakeTicket,
    MakeUser,
)


@pytest.fixture
def ana(make_user: MakeUser) -> Client:
    return make_user("Client", name="Ana")


@pytest.fixture
def raul(make_user: MakeUser) -> Representative:
    return make_user("Representative", name="Raúl")


@pytest.fixture
def rosa(make_user: MakeUser) -> Representative:
    return make_user("Representative", name="Rosa")


@pytest.fixture
def notebook(make_category: MakeCategory, make_product_type: MakeProductType) -> ProductType:
    return make_product_type(make_category("Hardware"), "Notebook")


@pytest.fixture
def xps(make_product: MakeProduct, notebook: ProductType) -> Product:
    return make_product(notebook, "XPS 13")


@pytest.fixture
def desktop(make_product: MakeProduct, notebook: ProductType) -> Product:
    return make_product(notebook, "Desktop")


@pytest.fixture
def raul_client(client: FlaskClient, login_as: LoginAs, raul: Representative) -> FlaskClient:
    login_as(client, raul)
    return client


def create_ticket(client: FlaskClient, **body: Any) -> Any:
    return client.post("/tickets", json=body)


def count(db_session: Session, table: Any) -> int:
    db_session.expire_all()
    return db_session.scalar(select(func.count()).select_from(table)) or 0


def stored_tickets(db_session: Session) -> list[Ticket]:
    db_session.expire_all()
    return list(db_session.scalars(select(Ticket).order_by(Ticket.id)))


def test_representative_creates_a_ticket_for_a_client(
    raul_client: FlaskClient,
    db_session: Session,
    ana: Client,
    raul: Representative,
    xps: Product,
    notebook: ProductType,
) -> None:
    """SPEC-TKT-01 · TC-TKT-01e"""
    response = create_ticket(
        raul_client, client_id=ana.id, first_message="Hola", product_ids=[xps.id]
    )

    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body["id"], int)
    assert body == {
        "id": body["id"],
        "state": "New",
        "client": {"id": ana.id, "name": "Ana"},
        "representative": {"id": raul.id, "name": "Raúl"},
        "products": [
            {
                "id": xps.id,
                "name": "XPS 13",
                "is_active": True,
                "product_type": {
                    "id": notebook.id,
                    "name": "Notebook",
                    "category_id": notebook.category_id,
                },
                "category": {"id": notebook.category_id, "name": "Hardware"},
            }
        ],
        "created_at": body["created_at"],
    }
    assert datetime.fromisoformat(body["created_at"]).utcoffset().total_seconds() == 0
    assert [ticket.id for ticket in stored_tickets(db_session)] == [body["id"]]


def test_create_ticket_ignores_the_representative_in_the_body(
    raul_client: FlaskClient,
    db_session: Session,
    ana: Client,
    raul: Representative,
    rosa: Representative,
) -> None:
    """SPEC-TKT-02 · TC-TKT-02c"""
    response = create_ticket(
        raul_client, client_id=ana.id, first_message="Hola", representative_id=rosa.id
    )

    assert response.status_code == 201
    assert response.get_json()["representative"]["id"] == raul.id
    assert [t.representative_id for t in stored_tickets(db_session)] == [raul.id]


def test_create_ticket_ignores_the_state_in_the_body(
    raul_client: FlaskClient, db_session: Session, ana: Client
) -> None:
    """SPEC-TKT-03 · TC-TKT-03b"""
    response = create_ticket(raul_client, client_id=ana.id, first_message="Hola", state="Closed")

    assert response.status_code == 201
    assert response.get_json()["state"] == "New"
    assert [t.state_name for t in stored_tickets(db_session)] == ["New"]


def test_create_ticket_stores_the_first_message_as_the_only_milestone(
    raul_client: FlaskClient, db_session: Session, ana: Client, raul: Representative
) -> None:
    """SPEC-TKT-04 · TC-TKT-04c"""
    response = create_ticket(raul_client, client_id=ana.id, first_message="Hola")

    db_session.expire_all()
    milestones = list(db_session.scalars(select(Milestone)))
    assert response.status_code == 201
    assert [(m.ticket_id, m.content, m.author_id) for m in milestones] == [
        (response.get_json()["id"], "Hola", raul.id)
    ]


def test_client_cannot_create_a_ticket(
    client: FlaskClient, login_as: LoginAs, db_session: Session, ana: Client
) -> None:
    """SPEC-TKT-05 · TC-TKT-05b"""
    login_as(client, ana)

    response = create_ticket(client, client_id=ana.id, first_message="Hola")

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert stored_tickets(db_session) == []


def test_client_gets_a_bad_request_for_an_invalid_body_and_forbidden_for_a_valid_one(
    client: FlaskClient, login_as: LoginAs, db_session: Session, ana: Client
) -> None:
    """SPEC-TKT-05 · TC-TKT-05d"""
    login_as(client, ana)

    invalid = create_ticket(client, first_message="")
    unknown_client = create_ticket(client, client_id=9999, first_message="Hola")

    assert invalid.status_code == 400
    assert invalid.get_json() == {
        "error": "validation_error",
        "fields": {"client_id": "required", "first_message": "required"},
    }
    assert unknown_client.status_code == 403
    assert unknown_client.get_json() == {"error": "forbidden"}
    assert stored_tickets(db_session) == []


@pytest.mark.parametrize("kind", ["unknown", "representative", "inactive"])
def test_create_ticket_rejects_an_invalid_client(
    kind: str,
    raul_client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    raul: Representative,
) -> None:
    """SPEC-TKT-06 · TC-TKT-06d"""
    client_id = {
        "unknown": 9999,
        "representative": raul.id,
        "inactive": make_user("Client", is_active=False).id,
    }[kind]

    response = create_ticket(raul_client, client_id=client_id, first_message="Hola")

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_client"}
    assert stored_tickets(db_session) == []


def test_create_ticket_rejects_a_client_id_out_of_range(
    raul_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-TKT-06 · TC-TKT-06e"""
    response = create_ticket(raul_client, client_id=2**63, first_message="Hola")

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_client"}
    assert stored_tickets(db_session) == []


@pytest.mark.parametrize("kind", ["unknown", "inactive", "out_of_range", "valid_and_inactive"])
def test_create_ticket_rejects_an_invalid_product(
    kind: str,
    raul_client: FlaskClient,
    db_session: Session,
    ana: Client,
    xps: Product,
    notebook: ProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-TKT-08 · TC-TKT-08j"""
    inactive = make_product(notebook, "Optiplex", is_active=False)
    product_ids = {
        "unknown": [9999],
        "inactive": [inactive.id],
        "out_of_range": [2**63],
        "valid_and_inactive": [xps.id, inactive.id],
    }[kind]

    response = create_ticket(
        raul_client, client_id=ana.id, first_message="Hola", product_ids=product_ids
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_product"}
    assert stored_tickets(db_session) == []


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({}, "required"),
        ({"first_message": "   "}, "required"),
        ({"first_message": 123}, "invalid"),
    ],
)
def test_create_ticket_rejects_an_invalid_first_message(
    body: dict[str, Any],
    expected: str,
    raul_client: FlaskClient,
    db_session: Session,
    ana: Client,
) -> None:
    """SPEC-TKT-23 · TC-TKT-23c"""
    response = create_ticket(raul_client, client_id=ana.id, **body)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"first_message": expected},
    }
    assert stored_tickets(db_session) == []


@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({"client_id": "abc"}, {"client_id": "invalid"}),
        ({"client_id": True}, {"client_id": "invalid"}),
        ({}, {"client_id": "required"}),
        ({"client_id": 1, "product_ids": "abc"}, {"product_ids": "invalid"}),
        ({"client_id": 1, "product_ids": [0]}, {"product_ids": "invalid"}),
    ],
)
def test_create_ticket_rejects_malformed_ids(
    body: dict[str, Any], fields: dict[str, str], raul_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-TKT-24 · TC-TKT-24e"""
    response = create_ticket(raul_client, first_message="Hola", **body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": fields}
    assert stored_tickets(db_session) == []


def test_create_ticket_rejects_a_null_client_id_as_required(
    raul_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-TKT-24 · TC-TKT-24h"""
    response = create_ticket(raul_client, client_id=None, first_message="Hola")

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": {"client_id": "required"}}
    assert stored_tickets(db_session) == []


def test_create_ticket_associates_several_products(
    raul_client: FlaskClient,
    db_session: Session,
    ana: Client,
    xps: Product,
    desktop: Product,
) -> None:
    """SPEC-TKT-31 · TC-TKT-31c"""
    response = create_ticket(
        raul_client, client_id=ana.id, first_message="Hola", product_ids=[xps.id, desktop.id]
    )

    assert response.status_code == 201
    body = response.get_json()
    assert sorted(p["id"] for p in body["products"]) == sorted([xps.id, desktop.id])
    assert count(db_session, ticket_products) == 2


def test_create_ticket_with_a_repeated_product_associates_it_once(
    raul_client: FlaskClient, db_session: Session, ana: Client, xps: Product
) -> None:
    """SPEC-TKT-31 · TC-TKT-31d"""
    response = create_ticket(
        raul_client, client_id=ana.id, first_message="Hola", product_ids=[xps.id, xps.id]
    )

    assert response.status_code == 201
    assert [p["id"] for p in response.get_json()["products"]] == [xps.id]
    assert count(db_session, ticket_products) == 1


@pytest.mark.parametrize("who", ["ana", "raul"])
def test_client_and_representative_read_the_ticket_detail(
    who: str,
    client: FlaskClient,
    login_as: LoginAs,
    make_ticket: MakeTicket,
    make_product: MakeProduct,
    notebook: ProductType,
    xps: Product,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-28 · TC-TKT-28c"""
    optiplex = make_product(notebook, "Optiplex", is_active=False)
    ticket = make_ticket(ana, raul, [xps, optiplex])
    login_as(client, {"ana": ana, "raul": raul}[who])

    response = client.get(f"/tickets/{ticket.id}")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "id": ticket.id,
        "state": "New",
        "client": {"id": ana.id, "name": "Ana"},
        "representative": {"id": raul.id, "name": "Raúl"},
        "products": [product_json(optiplex), product_json(xps)],
        "created_at": body["created_at"],
    }
    assert [p["is_active"] for p in body["products"]] == [False, True]
    assert datetime.fromisoformat(body["created_at"]).utcoffset().total_seconds() == 0


def test_a_client_lists_only_its_own_tickets(
    client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-17 · TC-TKT-17d"""
    beto = make_user("Client", name="Beto")
    mine = [make_ticket(ana, raul), make_ticket(ana, raul)]
    make_ticket(beto, raul)
    login_as(client, ana)

    response = client.get("/tickets")

    assert response.status_code == 200
    assert sorted(t["id"] for t in response.get_json()) == sorted(t.id for t in mine)

    login_as(client, make_user("Client", name="Carla"))
    assert client.get("/tickets").get_json() == []


def test_a_representative_lists_only_the_tickets_assigned_to_it(
    client: FlaskClient,
    login_as: LoginAs,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    rosa: Representative,
) -> None:
    """SPEC-TKT-18 · TC-TKT-18d"""
    mine = [make_ticket(ana, raul), make_ticket(ana, raul)]
    make_ticket(ana, rosa)
    login_as(client, raul)

    response = client.get("/tickets")

    assert response.status_code == 200
    assert sorted(t["id"] for t in response.get_json()) == sorted(t.id for t in mine)


@pytest.mark.parametrize("who", ["ana", "raul"])
def test_tickets_are_listed_newest_first(
    who: str,
    client: FlaskClient,
    login_as: LoginAs,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-29 · TC-TKT-29c"""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    middle = make_ticket(ana, raul, now=start + timedelta(hours=1))
    oldest = make_ticket(ana, raul, now=start)
    newest = make_ticket(ana, raul, now=start + timedelta(hours=2))
    login_as(client, {"ana": ana, "raul": raul}[who])

    response = client.get("/tickets")

    assert [t["id"] for t in response.get_json()] == [newest.id, middle.id, oldest.id]


def stored_state_changes(db_session: Session, ticket_id: int) -> list[tuple[str, int]]:
    db_session.expire_all()
    rows = db_session.execute(
        select(StateChange.state_name, StateChange.user_id)
        .where(StateChange.ticket_id == ticket_id)
        .order_by(StateChange.id)
    )
    return [tuple(row) for row in rows]


def test_client_closes_a_new_ticket(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-10 · TC-TKT-10e"""
    ticket = make_ticket(ana, raul)
    login_as(client, ana)

    response = client.post(f"/tickets/{ticket.id}/close")

    assert response.status_code == 200
    assert response.get_json()["state"] == "Closed"
    assert stored_tickets(db_session)[0].state_name == "Closed"


def test_representative_closes_an_in_progress_ticket(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-10 · TC-TKT-10f"""
    ticket = make_ticket(ana, raul)
    ticket.start_progress(raul, DEFAULT_TICKET_TIME)
    db_session.commit()
    login_as(client, raul)

    response = client.post(f"/tickets/{ticket.id}/close")

    assert response.status_code == 200
    assert response.get_json()["state"] == "Closed"


def test_closing_a_closed_ticket_is_an_invalid_transition(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-13 · TC-TKT-13e"""
    ticket = make_ticket(ana, raul)
    ticket.close(ana, DEFAULT_TICKET_TIME)
    db_session.commit()
    history = stored_state_changes(db_session, ticket.id)
    login_as(client, ana)

    response = client.post(f"/tickets/{ticket.id}/close")

    assert response.status_code == 409
    assert response.get_json() == {"error": "invalid_transition"}
    assert stored_tickets(db_session)[0].state_name == "Closed"
    assert stored_state_changes(db_session, ticket.id) == history


def test_closing_leaves_a_state_change_with_the_closing_user(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-14 · TC-TKT-14g"""
    ticket = make_ticket(ana, raul)
    login_as(client, ana)

    client.post(f"/tickets/{ticket.id}/close")

    assert stored_state_changes(db_session, ticket.id)[-1] == ("Closed", ana.id)
    assert len(stored_state_changes(db_session, ticket.id)) == 2


def close_ticket(db_session: Session, ticket: Ticket, user: Client | Representative) -> None:
    ticket.close(user, DEFAULT_TICKET_TIME)
    db_session.commit()


@pytest.mark.parametrize("who", ["ana", "raul"])
def test_reopening_a_closed_ticket_leaves_it_in_progress(
    who: str,
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-11 · TC-TKT-11d"""
    ticket = make_ticket(ana, raul)
    close_ticket(db_session, ticket, ana)
    login_as(client, {"ana": ana, "raul": raul}[who])

    response = client.post(f"/tickets/{ticket.id}/reopen")

    assert response.status_code == 200
    assert response.get_json()["state"] == "InProgress"
    assert stored_tickets(db_session)[0].state_name == "InProgress"


def test_the_assigned_representative_keeps_the_ticket_after_a_close_and_reopen(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-12 · TC-TKT-12c"""
    ticket = make_ticket(ana, raul)
    login_as(client, ana)

    closed = client.post(f"/tickets/{ticket.id}/close")
    reopened = client.post(f"/tickets/{ticket.id}/reopen")
    detail = client.get(f"/tickets/{ticket.id}")

    assert (closed.status_code, reopened.status_code) == (200, 200)
    assert detail.get_json()["state"] == "InProgress"
    assert detail.get_json()["representative"]["id"] == raul.id
    assert stored_tickets(db_session)[0].representative_id == raul.id


def test_reopening_a_ticket_that_is_not_closed_is_an_invalid_transition(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-13 · TC-TKT-13f"""
    new = make_ticket(ana, raul)
    in_progress = make_ticket(ana, raul)
    in_progress.start_progress(raul, DEFAULT_TICKET_TIME)
    db_session.commit()
    histories = {t.id: stored_state_changes(db_session, t.id) for t in (new, in_progress)}
    login_as(client, ana)

    responses = [client.post(f"/tickets/{t.id}/reopen") for t in (new, in_progress)]

    assert [r.status_code for r in responses] == [409, 409]
    assert [r.get_json() for r in responses] == [{"error": "invalid_transition"}] * 2
    assert [t.state_name for t in stored_tickets(db_session)] == ["New", "InProgress"]
    assert histories == {t.id: stored_state_changes(db_session, t.id) for t in (new, in_progress)}


def post_products(client: FlaskClient, ticket: Ticket, **body: Any) -> Any:
    return client.post(f"/tickets/{ticket.id}/products", json=body)


def stored_product_ids(db_session: Session, ticket_id: int) -> list[int]:
    db_session.expire_all()
    rows = db_session.scalars(
        select(ticket_products.c.product_id)
        .where(ticket_products.c.ticket_id == ticket_id)
        .order_by(ticket_products.c.product_id)
    )
    return list(rows)


def test_the_assigned_representative_adds_a_product(
    raul_client: FlaskClient,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    xps: Product,
) -> None:
    """SPEC-TKT-07 · TC-TKT-07d"""
    ticket = make_ticket(ana, raul)

    response = post_products(raul_client, ticket, product_ids=[xps.id])

    assert response.status_code == 200
    assert [p["id"] for p in response.get_json()["products"]] == [xps.id]
    assert stored_product_ids(db_session, ticket.id) == [xps.id]


def test_products_can_be_added_to_a_closed_ticket(
    raul_client: FlaskClient,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    xps: Product,
) -> None:
    """SPEC-TKT-07 · TC-TKT-07f"""
    ticket = make_ticket(ana, raul)
    close_ticket(db_session, ticket, ana)
    history = stored_state_changes(db_session, ticket.id)

    response = post_products(raul_client, ticket, product_ids=[xps.id])

    assert response.status_code == 200
    assert response.get_json()["state"] == "Closed"
    assert [p["id"] for p in response.get_json()["products"]] == [xps.id]
    assert stored_product_ids(db_session, ticket.id) == [xps.id]
    assert stored_state_changes(db_session, ticket.id) == history


@pytest.mark.parametrize("kind", ["unknown", "inactive", "out_of_range", "valid_and_inactive"])
def test_adding_an_invalid_product_changes_nothing(
    kind: str,
    raul_client: FlaskClient,
    db_session: Session,
    make_ticket: MakeTicket,
    make_product: MakeProduct,
    notebook: ProductType,
    ana: Client,
    raul: Representative,
    xps: Product,
) -> None:
    """SPEC-TKT-08 · TC-TKT-08k"""
    ticket = make_ticket(ana, raul)
    inactive = make_product(notebook, "Optiplex", is_active=False)
    product_ids = {
        "unknown": [9999],
        "inactive": [inactive.id],
        "out_of_range": [2**63],
        "valid_and_inactive": [xps.id, inactive.id],
    }[kind]

    response = post_products(raul_client, ticket, product_ids=product_ids)

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_product"}
    assert stored_product_ids(db_session, ticket.id) == []


def test_the_client_cannot_add_products_to_its_own_ticket(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    xps: Product,
) -> None:
    """SPEC-TKT-22 · TC-TKT-22c"""
    ticket = make_ticket(ana, raul)
    login_as(client, ana)

    response = post_products(client, ticket, product_ids=[xps.id])

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert stored_product_ids(db_session, ticket.id) == []


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({}, "required"),
        ({"product_ids": None}, "required"),
        ({"product_ids": "abc"}, "invalid"),
        ({"product_ids": [0]}, "invalid"),
        ({"product_ids": ["1"]}, "invalid"),
        ({"product_ids": []}, "invalid"),
    ],
)
def test_adding_products_rejects_a_malformed_product_ids(
    body: dict[str, Any],
    expected: str,
    raul_client: FlaskClient,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-24 · TC-TKT-24f"""
    ticket = make_ticket(ana, raul)

    response = post_products(raul_client, ticket, **body)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"product_ids": expected},
    }
    assert stored_product_ids(db_session, ticket.id) == []


def test_adding_the_same_product_twice_keeps_one_association(
    raul_client: FlaskClient,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    xps: Product,
    desktop: Product,
) -> None:
    """SPEC-TKT-25 · TC-TKT-25c"""
    ticket = make_ticket(ana, raul)

    responses = [
        post_products(raul_client, ticket, product_ids=[xps.id]),
        post_products(raul_client, ticket, product_ids=[xps.id]),
        post_products(raul_client, ticket, product_ids=[desktop.id, desktop.id]),
    ]

    assert [r.status_code for r in responses] == [200, 200, 200]
    assert stored_product_ids(db_session, ticket.id) == sorted([xps.id, desktop.id])


def test_the_assigned_representative_removes_a_product(
    raul_client: FlaskClient,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    xps: Product,
) -> None:
    """SPEC-TKT-21 · TC-TKT-21d"""
    ticket = make_ticket(ana, raul, [xps])

    response = raul_client.delete(f"/tickets/{ticket.id}/products/{xps.id}")

    assert response.status_code == 204
    assert response.data == b""
    assert stored_product_ids(db_session, ticket.id) == []
    assert db_session.get(Product, xps.id) is not None


def test_products_can_be_removed_from_a_closed_ticket(
    raul_client: FlaskClient,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    xps: Product,
) -> None:
    """SPEC-TKT-21 · TC-TKT-21f"""
    ticket = make_ticket(ana, raul, [xps])
    close_ticket(db_session, ticket, ana)

    response = raul_client.delete(f"/tickets/{ticket.id}/products/{xps.id}")

    assert response.status_code == 204
    assert stored_product_ids(db_session, ticket.id) == []
    assert stored_tickets(db_session)[0].state_name == "Closed"


def test_the_client_cannot_remove_products_from_its_own_ticket(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    xps: Product,
) -> None:
    """SPEC-TKT-22 · TC-TKT-22d"""
    ticket = make_ticket(ana, raul, [xps])
    login_as(client, ana)

    response = client.delete(f"/tickets/{ticket.id}/products/{xps.id}")

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}
    assert stored_product_ids(db_session, ticket.id) == [xps.id]


def test_removing_a_product_that_is_not_in_the_ticket_is_not_found(
    raul_client: FlaskClient,
    db_session: Session,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    xps: Product,
    desktop: Product,
) -> None:
    """SPEC-TKT-26 · TC-TKT-26c"""
    ticket = make_ticket(ana, raul, [xps])

    response = raul_client.delete(f"/tickets/{ticket.id}/products/{desktop.id}")

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_not_in_ticket"}
    assert stored_product_ids(db_session, ticket.id) == [xps.id]


@pytest.mark.parametrize("product_id", [9999, 2**63])
def test_removing_an_unknown_or_out_of_range_product_is_not_found(
    product_id: int,
    raul_client: FlaskClient,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-26 · TC-TKT-26d"""
    ticket = make_ticket(ana, raul)

    response = raul_client.delete(f"/tickets/{ticket.id}/products/{product_id}")

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_not_in_ticket"}


def test_there_is_no_way_to_delete_or_modify_tickets_or_their_history(app: Flask) -> None:
    """SPEC-TKT-16 · TC-TKT-16j"""
    forbidden_prefixes = ("delete", "remove", "update")
    public = [name for name in dir(SqlAlchemyTicketRepository) if not name.startswith("_")]
    rules = [rule for rule in app.url_map.iter_rules() if rule.rule.startswith("/tickets")]
    ticket_rule = next(rule for rule in rules if rule.rule == "/tickets/<int:ticket_id>")

    assert [name for name in public if name.startswith(forbidden_prefixes)] == []
    assert not {"DELETE", "PUT", "PATCH"} & ticket_rule.methods
    state_rules = [rule for rule in rules if "state" in rule.rule]
    assert [rule.rule for rule in state_rules] == ["/tickets/<int:ticket_id>/state-changes"]
    assert state_rules[0].methods - {"HEAD", "OPTIONS"} == {"GET"}
    milestone_methods = {m for rule in rules if "milestone" in rule.rule for m in rule.methods}
    assert not {"DELETE", "PUT", "PATCH"} & milestone_methods


@pytest.fixture
def history_ticket(
    db_session: Session, make_ticket: MakeTicket, ana: Client, raul: Representative
) -> Ticket:
    """A ticket of ana and raul that ana closed and raul reopened, one hour apart."""
    ticket = make_ticket(ana, raul)
    ticket.close(ana, DEFAULT_TICKET_TIME + timedelta(hours=1))
    ticket.reopen(raul, DEFAULT_TICKET_TIME + timedelta(hours=2))
    db_session.commit()
    return ticket


def expected_history(ana: Client, raul: Representative) -> list[tuple[str, int]]:
    return [("New", raul.id), ("Closed", ana.id), ("InProgress", raul.id)]


@pytest.mark.parametrize("who", ["ana", "raul"])
def test_client_and_representative_read_the_state_history(
    who: str,
    client: FlaskClient,
    login_as: LoginAs,
    history_ticket: Ticket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-35 · TC-TKT-35d"""
    login_as(client, {"ana": ana, "raul": raul}[who])

    response = client.get(f"/tickets/{history_ticket.id}/state-changes")

    assert response.status_code == 200
    body = response.get_json()
    assert [(c["state"], c["user"]["id"]) for c in body] == expected_history(ana, raul)


def test_admin_reads_the_same_state_history(
    client: FlaskClient,
    admin_client: FlaskClient,
    login_as: LoginAs,
    history_ticket: Ticket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-35 · TC-TKT-35f"""
    login_as(client, ana)
    expected = client.get(f"/tickets/{history_ticket.id}/state-changes")

    response = admin_client.get(f"/tickets/{history_ticket.id}/state-changes")

    assert response.status_code == 200
    assert response.get_json() == expected.get_json()
    assert len(response.get_json()) == 3


def test_a_state_change_exposes_state_user_and_timestamp(
    client: FlaskClient,
    login_as: LoginAs,
    history_ticket: Ticket,
    ana: Client,
    raul: Representative,
) -> None:
    """SPEC-TKT-36 · TC-TKT-36a"""
    login_as(client, ana)

    body = client.get(f"/tickets/{history_ticket.id}/state-changes").get_json()

    assert all(set(change) == {"state", "user", "timestamp"} for change in body)
    assert all(set(change["user"]) == {"id", "name", "role"} for change in body)
    assert body[1]["user"] == {"id": ana.id, "name": "Ana", "role": "Client"}
    assert body[2]["user"] == {"id": raul.id, "name": "Raúl", "role": "Representative"}
    expected = [DEFAULT_TICKET_TIME + timedelta(hours=h) for h in (0, 1, 2)]
    for change, instant in zip(body, expected, strict=True):
        assert change["timestamp"].endswith("+00:00")
        assert datetime.fromisoformat(change["timestamp"]) == instant


def test_the_state_change_schema_is_documented(client: FlaskClient) -> None:
    """SPEC-TKT-36 · TC-TKT-36b"""
    contract = client.get("/openapi.json").get_json()
    schema = contract["components"]["schemas"]["StateChange"]
    ok = contract["paths"]["/tickets/{ticket_id}/state-changes"]["get"]["responses"]["200"]

    assert set(schema["properties"]) == {"state", "user", "timestamp"}
    assert set(schema["required"]) == {"state", "user", "timestamp"}
    assert schema["properties"]["state"]["enum"] == ["New", "InProgress", "Closed"]
    assert schema["properties"]["user"] == {"$ref": "#/components/schemas/MilestoneAuthor"}
    assert schema["properties"]["timestamp"]["format"] == "date-time"
    assert ok["content"]["application/json"]["schema"] == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/StateChange"},
    }


def test_the_state_history_is_not_paged(
    client: FlaskClient, login_as: LoginAs, history_ticket: Ticket, ana: Client
) -> None:
    """SPEC-TKT-47 · TC-TKT-47a"""
    login_as(client, ana)
    base = f"/tickets/{history_ticket.id}/state-changes"

    for query in ("?page=1&page_size=1", "?page=abc"):
        response = client.get(base + query)

        assert response.status_code == 200
        assert len(response.get_json()) == 3


@pytest.fixture
def listing_data(
    db_session: Session,
    make_user: MakeUser,
    make_ticket: MakeTicket,
    ana: Client,
    raul: Representative,
    rosa: Representative,
) -> dict[str, Ticket]:
    """Four tickets, oldest first: t1 ana/raul, t2 beto/raul, t3 ana/rosa (closed), t4 beto/rosa."""
    beto = make_user("Client", name="Beto")
    start = datetime(2026, 1, 1, tzinfo=UTC)
    t1 = make_ticket(ana, raul, first_message="El router no anda", now=start)
    t2 = make_ticket(beto, raul, now=start + timedelta(hours=1))
    t3 = make_ticket(ana, rosa, now=start + timedelta(hours=2))
    t4 = make_ticket(beto, rosa, first_message="Cambiar router", now=start + timedelta(hours=3))
    t3.close(ana, start + timedelta(hours=4))
    db_session.commit()
    return {"t1": t1, "t2": t2, "t3": t3, "t4": t4}


def listed_ids(response: Any) -> list[int]:
    assert response.status_code == 200
    return [t["id"] for t in response.get_json()]


def test_a_client_filters_its_tickets_by_state(
    client: FlaskClient, login_as: LoginAs, ana: Client, listing_data: dict[str, Ticket]
) -> None:
    """SPEC-TKT-38 · TC-TKT-38c"""
    login_as(client, ana)

    assert listed_ids(client.get("/tickets?state=New")) == [listing_data["t1"].id]


def test_a_representative_filters_by_client_and_an_unknown_id_gives_an_empty_list(
    client: FlaskClient,
    admin_client: FlaskClient,
    login_as: LoginAs,
    raul: Representative,
    ana: Client,
    listing_data: dict[str, Ticket],
) -> None:
    """SPEC-TKT-39 · TC-TKT-39d"""
    login_as(client, raul)

    assert listed_ids(client.get(f"/tickets?client_id={ana.id}")) == [listing_data["t1"].id]
    assert listed_ids(admin_client.get("/tickets?client_id=99999999999999999999")) == []


def test_admin_filters_by_representative_and_client(
    admin_client: FlaskClient,
    rosa: Representative,
    ana: Client,
    listing_data: dict[str, Ticket],
) -> None:
    """SPEC-TKT-40 · TC-TKT-40c"""
    only_rosa = admin_client.get(f"/tickets?representative_id={rosa.id}")
    both = admin_client.get(f"/tickets?representative_id={rosa.id}&client_id={ana.id}")

    assert listed_ids(only_rosa) == [listing_data["t4"].id, listing_data["t3"].id]
    assert listed_ids(both) == [listing_data["t3"].id]


def test_search_never_widens_the_visibility_of_the_role(
    client: FlaskClient, login_as: LoginAs, rosa: Representative, listing_data: dict[str, Ticket]
) -> None:
    """SPEC-TKT-41 · TC-TKT-41e"""
    login_as(client, rosa)

    assert listed_ids(client.get("/tickets?q=router")) == [listing_data["t4"].id]


@pytest.mark.parametrize("query", ["q=", "q=%20"])
def test_a_blank_search_behaves_as_if_it_was_not_sent(
    query: str,
    client: FlaskClient,
    login_as: LoginAs,
    ana: Client,
    listing_data: dict[str, Ticket],
) -> None:
    """SPEC-TKT-41 · TC-TKT-41f"""
    login_as(client, ana)

    assert listed_ids(client.get(f"/tickets?{query}")) == [
        listing_data["t3"].id,
        listing_data["t1"].id,
    ]


def test_order_asc_lists_the_oldest_first(
    client: FlaskClient, login_as: LoginAs, ana: Client, listing_data: dict[str, Ticket]
) -> None:
    """SPEC-TKT-42 · TC-TKT-42c"""
    login_as(client, ana)

    assert listed_ids(client.get("/tickets?order=asc")) == [
        listing_data["t1"].id,
        listing_data["t3"].id,
    ]


def test_invalid_listing_parameters_are_rejected_together(
    admin_client: FlaskClient, listing_data: dict[str, Ticket]
) -> None:
    """SPEC-TKT-43 · TC-TKT-43b"""
    cases = {
        "state=closed": {"state": "invalid"},
        "client_id=abc": {"client_id": "invalid"},
        "order=up&representative_id=0": {"order": "invalid", "representative_id": "invalid"},
    }

    for query, fields in cases.items():
        response = admin_client.get(f"/tickets?{query}")
        assert response.status_code == 400
        assert response.get_json() == {"error": "validation_error", "fields": fields}


def test_the_state_parameter_documents_its_three_values(client: FlaskClient) -> None:
    """SPEC-TKT-43 · TC-TKT-43c"""
    contract = client.get("/openapi.json").get_json()
    declared = contract["paths"]["/tickets"]["get"]["parameters"]
    resolved = [contract["components"]["parameters"][p["$ref"].split("/")[-1]] for p in declared]
    state = next(p for p in resolved if p["name"] == "state")

    assert state["schema"] == {"type": "string", "enum": ["New", "InProgress", "Closed"]}


def test_a_filter_cannot_reveal_tickets_of_other_representatives(
    client: FlaskClient,
    login_as: LoginAs,
    raul: Representative,
    ana: Client,
    listing_data: dict[str, Ticket],
) -> None:
    """SPEC-TKT-44 · TC-TKT-44c"""
    login_as(client, raul)

    assert listed_ids(client.get(f"/tickets?client_id={ana.id}&state=InProgress")) == []


def test_admin_pages_the_tickets(
    admin_client: FlaskClient, listing_data: dict[str, Ticket]
) -> None:
    """SPEC-TKT-45 · TC-TKT-45b"""
    t = listing_data
    plain = admin_client.get("/tickets")
    paged = admin_client.get("/tickets?page=1&page_size=2")
    filtered = admin_client.get("/tickets?page_size=2&state=New")

    assert isinstance(plain.get_json(), list)
    assert [i["id"] for i in paged.get_json()["items"]] == [t["t4"].id, t["t3"].id]
    assert {k: v for k, v in paged.get_json().items() if k != "items"} == {
        "page": 1,
        "page_size": 2,
        "total": 4,
    }
    assert [i["id"] for i in filtered.get_json()["items"]] == [t["t4"].id, t["t2"].id]
    assert filtered.get_json()["total"] == 3


def test_the_total_counts_only_what_the_client_may_see(
    client: FlaskClient, login_as: LoginAs, ana: Client, listing_data: dict[str, Ticket]
) -> None:
    """SPEC-TKT-45 · TC-TKT-45c"""
    login_as(client, ana)

    body = client.get("/tickets?page=1").get_json()

    assert [i["id"] for i in body["items"]] == [listing_data["t3"].id, listing_data["t1"].id]
    assert (body["page"], body["page_size"], body["total"]) == (1, 20, 2)


def test_a_page_beyond_the_last_is_empty_with_the_real_total(
    admin_client: FlaskClient, listing_data: dict[str, Ticket]
) -> None:
    """SPEC-TKT-45 · TC-TKT-45d"""
    response = admin_client.get("/tickets?page=9&page_size=2")

    assert response.status_code == 200
    assert response.get_json()["items"] == []
    assert response.get_json()["total"] == 4


def test_invalid_paging_values_are_rejected(
    client: FlaskClient, login_as: LoginAs, ana: Client
) -> None:
    """SPEC-TKT-45 · TC-TKT-45f"""
    login_as(client, ana)

    zero = client.get("/tickets?page=0")
    huge = client.get("/tickets?page_size=101")

    assert zero.status_code == huge.status_code == 400
    assert zero.get_json()["fields"] == {"page": "invalid"}
    assert huge.get_json()["fields"] == {"page_size": "invalid"}


def test_filters_forbidden_to_the_role_are_rejected(
    client: FlaskClient,
    login_as: LoginAs,
    ana: Client,
    raul: Representative,
    listing_data: dict[str, Ticket],
) -> None:
    """SPEC-TKT-46 · TC-TKT-46b"""
    login_as(client, ana)
    own_client = client.get(f"/tickets?client_id={ana.id}")
    other_rep = client.get(f"/tickets?representative_id={raul.id}")
    login_as(client, raul)
    own_rep = client.get(f"/tickets?representative_id={raul.id}")

    for response in (own_client, other_rep, own_rep):
        assert response.status_code == 403
        assert response.get_json() == {"error": "forbidden"}


def test_the_format_check_comes_before_the_forbidden_filters(
    client: FlaskClient,
    login_as: LoginAs,
    ana: Client,
    raul: Representative,
    listing_data: dict[str, Ticket],
) -> None:
    """SPEC-TKT-48 · TC-TKT-48b"""
    login_as(client, raul)
    by_state = client.get(f"/tickets?state=foo&representative_id={raul.id}")
    login_as(client, ana)
    by_order = client.get(f"/tickets?order=x&client_id={ana.id}")

    for response in (by_state, by_order):
        assert response.status_code == 400
        assert response.get_json()["error"] == "validation_error"
