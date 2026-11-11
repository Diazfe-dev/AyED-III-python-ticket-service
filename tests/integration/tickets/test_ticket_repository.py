import pytest
from flask import Flask
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.domain.ticket import Ticket
from app.domain.users import User
from app.repositories.ticket_repository import SqlAlchemyTicketRepository
from tests.conftest import (
    DEFAULT_TICKET_TIME,
    MakeCategory,
    MakeProduct,
    MakeProductType,
    MakeTicket,
    MakeUser,
)
from tests.integration.catalog.queries import count_statements


def new_session(app: Flask) -> Session:
    return app.extensions[EXTENSION_KEY]["session_factory"]()


def test_get_visible_returns_the_ticket_only_to_its_client(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-19 · TC-TKT-19b"""
    ana = make_user("Client", name="Ana")
    beto = make_user("Client", name="Beto")
    raul = make_user("Representative", name="Raul")
    ticket = make_ticket(ana, raul)
    repository = SqlAlchemyTicketRepository(db_session)

    assert repository.get_visible(ticket.id, beto) is None
    assert repository.get_visible(ticket.id, ana) is ticket
    assert repository.get_visible(2**63, ana) is None


def test_get_visible_returns_the_ticket_to_its_representative_but_not_to_another(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-20 · TC-TKT-20b"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    rosa = make_user("Representative", name="Rosa")
    ticket = make_ticket(ana, raul)
    repository = SqlAlchemyTicketRepository(db_session)

    assert repository.get_visible(ticket.id, rosa) is None
    assert repository.get_visible(ticket.id, raul) is ticket


@pytest.mark.parametrize("ticket_id", [9999, 2**63, 99999999999999999999])
def test_get_visible_returns_none_for_missing_or_out_of_range_ids(
    db_session: Session, make_user: MakeUser, ticket_id: int
) -> None:
    """SPEC-TKT-30 · TC-TKT-30b"""
    ana = make_user("Client", name="Ana")

    assert SqlAlchemyTicketRepository(db_session).get_visible(ticket_id, ana) is None


def test_get_visible_loads_everything_the_detail_needs_in_few_statements(
    app: Flask,
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
) -> None:
    """SPEC-TKT-28 · TC-TKT-28d"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    notebook = make_product_type(make_category("Hardware"), "Notebook")
    editor = make_product_type(make_category("Software"), "Editor")
    products = [
        make_product(notebook, "XPS 13"),
        make_product(notebook, "ThinkPad"),
        make_product(editor, "Vim"),
    ]
    ticket_id, ana_id = make_ticket(ana, raul, products).id, ana.id

    with new_session(app) as session:
        actor = session.get(User, ana_id)
        with count_statements(session) as statements:
            ticket = SqlAlchemyTicketRepository(session).get_visible(ticket_id, actor)
            assert ticket is not None
            assert ticket.client.name == "Ana"
            assert ticket.representative.name == "Raul"
            assert [p.product_type.category.name for p in ticket.products]

        assert len(statements) <= 6


def test_added_ticket_gets_its_id_on_flush_without_committing(
    db_session: Session, make_user: MakeUser
) -> None:
    """SPEC-TKT-01 · TC-TKT-01b"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    ticket = Ticket.open(ana, raul, [], "Hola", DEFAULT_TICKET_TIME)

    SqlAlchemyTicketRepository(db_session).add(ticket)

    assert ticket.id is not None
    ticket_id = ticket.id
    db_session.rollback()
    assert db_session.get(Ticket, ticket_id) is None
