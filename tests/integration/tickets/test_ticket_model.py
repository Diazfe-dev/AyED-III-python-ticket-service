from datetime import UTC, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.products import Product
from app.domain.ticket import Ticket
from tests.conftest import (
    DEFAULT_TICKET_TIME,
    MakeCategory,
    MakeProduct,
    MakeProductType,
    MakeTicket,
    MakeUser,
)


def test_ticket_keeps_client_and_representative_apart(
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
):
    """SPEC-TKT-01 · TC-TKT-01b"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    xps = make_product(make_product_type(make_category()), name="XPS 13")
    ticket = make_ticket(ana, raul, [xps])
    ticket_id, ana_id, raul_id, xps_id = ticket.id, ana.id, raul.id, xps.id
    db_session.close()

    loaded = db_session.get(Ticket, ticket_id)

    assert loaded.client_id == ana_id
    assert loaded.representative_id == raul_id
    assert loaded.client.name == "Ana"
    assert loaded.representative.name == "Raul"
    assert [product.id for product in loaded.products] == [xps_id]
    assert [t.id for t in loaded.client.tickets] == [ticket_id]
    assert [t.id for t in loaded.representative.assigned_tickets] == [ticket_id]


def test_first_milestone_is_saved_with_its_author_and_utc_date(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-04 · TC-TKT-04b"""
    raul = make_user("Representative")
    ticket = make_ticket(make_user("Client"), raul)
    ticket_id, raul_id = ticket.id, raul.id
    db_session.close()

    milestone = db_session.get(Ticket, ticket_id).milestones[0]

    assert milestone.ticket_id == ticket_id
    assert milestone.author_id == raul_id
    assert milestone.content == "Hola"
    assert milestone.created_at == DEFAULT_TICKET_TIME
    assert milestone.created_at.utcoffset().total_seconds() == 0


def test_ticket_products_are_stored_in_the_association_table_ordered_by_name(
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
):
    """SPEC-TKT-07 · TC-TKT-07b"""
    product_type = make_product_type(make_category())
    zeta = make_product(product_type, name="Zeta")
    alpha = make_product(product_type, name="Alpha")
    ticket = make_ticket(make_user("Client"), make_user("Representative"), [zeta, alpha])
    ticket_id, alpha_id, zeta_id = ticket.id, alpha.id, zeta.id
    db_session.close()

    loaded = db_session.get(Ticket, ticket_id)
    rows = db_session.execute(
        text("SELECT COUNT(*) FROM ticket_products WHERE ticket_id = :id"), {"id": ticket_id}
    ).scalar_one()

    assert [product.id for product in loaded.products] == [alpha_id, zeta_id]
    assert rows == 2


def test_initial_state_change_is_saved_with_user_state_and_utc_date(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-15 · TC-TKT-15b"""
    raul = make_user("Representative")
    ticket = make_ticket(make_user("Client"), raul)
    ticket_id, raul_id = ticket.id, raul.id
    db_session.close()

    change = db_session.get(Ticket, ticket_id).state_history[0]

    assert change.ticket_id == ticket_id
    assert change.user_id == raul_id
    assert change.state_name == "New"
    assert change.timestamp == DEFAULT_TICKET_TIME
    assert change.timestamp.utcoffset().total_seconds() == 0


def test_closed_state_change_is_read_back_in_utc(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-14 · TC-TKT-14c"""
    ana = make_user("Client")
    ticket = make_ticket(ana, make_user("Representative"))
    closed_at = DEFAULT_TICKET_TIME + timedelta(hours=1)
    ticket.close(ana, closed_at)
    db_session.commit()
    ticket_id = ticket.id
    db_session.close()

    change = db_session.get(Ticket, ticket_id).state_history[-1]

    assert change.state_name == "Closed"
    assert change.timestamp.tzinfo is UTC
    assert change.timestamp == closed_at


def test_removed_product_leaves_the_association_and_stays_in_the_catalog(
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
):
    """SPEC-TKT-21 · TC-TKT-21b"""
    xps = make_product(make_product_type(make_category()), name="XPS 13")
    ticket = make_ticket(make_user("Client"), make_user("Representative"), [xps])
    ticket_id, xps_id = ticket.id, xps.id
    ticket.remove_product(xps)
    db_session.commit()
    db_session.close()

    links = db_session.execute(
        text("SELECT COUNT(*) FROM ticket_products WHERE ticket_id = :id"), {"id": ticket_id}
    ).scalar_one()
    product = db_session.get(Product, xps_id)

    assert links == 0
    assert (product.name, product.is_active) == ("XPS 13", True)


def test_duplicate_association_is_rejected_by_the_composite_primary_key(
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
):
    """SPEC-TKT-25 · TC-TKT-25d"""
    xps = make_product(make_product_type(make_category()))
    ticket = make_ticket(make_user("Client"), make_user("Representative"), [xps])
    params = {"ticket_id": ticket.id, "product_id": xps.id}

    with pytest.raises(IntegrityError):
        db_session.execute(
            text("INSERT INTO ticket_products VALUES (:ticket_id, :product_id)"), params
        )
