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
    assert [rule.rule for rule in rules if "state" in rule.rule] == []
    assert [rule.rule for rule in rules if "milestone" in rule.rule] == []
