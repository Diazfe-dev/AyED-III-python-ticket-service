import pytest
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.milestone import Milestone
from app.domain.state_change import StateChange
from app.domain.ticket import Ticket, ticket_products
from tests.conftest import (
    LoginAs,
    MakeCategory,
    MakeProduct,
    MakeProductType,
    MakeTicket,
    MakeUser,
)


def count_rows(db_session: Session, model: type, ticket_id: int) -> int:
    db_session.expire_all()
    statement = select(func.count()).select_from(model).where(model.ticket_id == ticket_id)
    return db_session.scalar(statement) or 0


@pytest.mark.parametrize(
    ("deactivated_role", "party_key", "other_key"),
    [
        ("Client", "client", "representative"),
        ("Representative", "representative", "client"),
    ],
)
def test_ticket_of_a_deactivated_user_keeps_its_history_and_stays_readable(
    admin_client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    make_ticket: MakeTicket,
    login_as: LoginAs,
    deactivated_role: str,
    party_key: str,
    other_key: str,
) -> None:
    """SPEC-USR-10 · TC-USR-10d"""
    ana = make_user("Client", name="Ana", email="ana@x.com")
    raul = make_user("Representative", name="Raúl", email="raul@x.com")
    ticket_id = make_ticket(ana, raul).id
    deactivated, other = (ana, raul) if deactivated_role == "Client" else (raul, ana)
    deactivated_id, other_id, deactivated_email = deactivated.id, other.id, deactivated.email
    assert db_session.get(Ticket, ticket_id) is not None
    assert count_rows(db_session, Milestone, ticket_id) == 1
    assert count_rows(db_session, StateChange, ticket_id) == 1

    response = admin_client.post(f"/users/{deactivated_id}/deactivate")

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Ticket, ticket_id) is not None
    assert count_rows(db_session, Milestone, ticket_id) == 1
    assert count_rows(db_session, StateChange, ticket_id) == 1
    login_as(admin_client, other)
    read = admin_client.get(f"/tickets/{ticket_id}")
    assert read.status_code == 200
    assert read.get_json()[party_key]["id"] == deactivated_id
    assert read.get_json()[other_key]["id"] == other_id
    login = admin_client.post("/login", json={"email": deactivated_email, "password": "password1"})
    assert login.status_code == 401


def test_deactivated_product_stays_in_its_tickets_and_cannot_be_associated_again(
    admin_client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    make_ticket: MakeTicket,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    login_as: LoginAs,
) -> None:
    """SPEC-PRD-06 · TC-PRD-06d"""
    ana = make_user("Client", name="Ana", email="ana@x.com")
    raul = make_user("Representative", name="Raúl", email="raul@x.com")
    notebook = make_product_type(make_category("Computers"), "Notebook")
    xps = make_product(notebook, "XPS 13")
    ticket_id = make_ticket(ana, raul, [xps]).id
    other_ticket_id = make_ticket(ana, raul).id
    xps_id = xps.id

    response = admin_client.post(f"/products/{xps_id}/deactivate")

    assert response.status_code == 200
    login_as(admin_client, raul)
    read = admin_client.get(f"/tickets/{ticket_id}")
    assert read.status_code == 200
    products = read.get_json()["products"]
    assert [(p["id"], p["is_active"]) for p in products] == [(xps_id, False)]
    db_session.expire_all()
    stored = db_session.scalars(
        select(ticket_products.c.product_id).where(ticket_products.c.ticket_id == ticket_id)
    ).all()
    assert list(stored) == [xps_id]
    created = admin_client.post(
        "/tickets", json={"client_id": ana.id, "first_message": "Hola", "product_ids": [xps_id]}
    )
    assert created.status_code == 400
    assert created.get_json() == {"error": "invalid_product"}
    added = admin_client.post(
        f"/tickets/{other_ticket_id}/products", json={"product_ids": [xps_id]}
    )
    assert added.status_code == 400
    assert added.get_json() == {"error": "invalid_product"}
