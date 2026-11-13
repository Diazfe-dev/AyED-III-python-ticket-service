from collections.abc import Iterable
from datetime import timedelta
from typing import NamedTuple

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.domain.paging import Page, PageRequest
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


def test_get_finds_any_ticket_without_a_participant_filter(
    app: Flask,
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
) -> None:
    """SPEC-TKT-34 · TC-TKT-34b"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    notebook = make_product_type(make_category("Hardware"), "Notebook")
    editor = make_product_type(make_category("Software"), "Editor")
    products = [
        make_product(notebook, "XPS 13"),
        make_product(notebook, "ThinkPad"),
        make_product(editor, "Vim"),
    ]
    ticket = make_ticket(ana, raul, products)
    ticket_id = ticket.id

    with new_session(app) as session:
        repository = SqlAlchemyTicketRepository(session)
        with count_statements(session) as statements:
            found = repository.get(ticket_id)
            assert found is not None
            assert found.client.name == "Ana"
            assert found.representative.name == "Raul"
            assert [p.product_type.category.name for p in found.products]
        assert len(statements) <= 6

        assert repository.get(9999) is None
        assert repository.get(2**63) is None
        with_milestones = repository.get_with_milestones(ticket_id)
        assert with_milestones is not None
        assert [m.content for m in with_milestones.milestones] == ["Hola"]
        assert [m.author.name for m in with_milestones.milestones] == ["Raul"]
        assert repository.get_with_milestones(9999) is None


def test_get_visible_with_history_orders_changes_by_timestamp_then_id(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-35 · TC-TKT-35b"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    ticket = make_ticket(ana, raul)
    later = DEFAULT_TICKET_TIME + timedelta(hours=1)
    ticket.start_progress(raul, later)
    ticket.close(ana, later)
    db_session.commit()
    db_session.expire_all()

    found = SqlAlchemyTicketRepository(db_session).get_visible_with_history(ticket.id, ana)

    assert found is not None
    assert [c.state_name for c in found.state_history] == ["New", "InProgress", "Closed"]
    assert [c.timestamp for c in found.state_history] == [DEFAULT_TICKET_TIME, later, later]
    ids = [c.id for c in found.state_history]
    assert ids == sorted(ids)


def test_get_with_history_loads_the_change_users_without_n_plus_one(
    app: Flask, db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-35 · TC-TKT-35c"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    ticket = make_ticket(ana, raul)
    for hours, (user, move) in enumerate(
        [
            (raul, Ticket.start_progress),
            (ana, Ticket.close),
            (ana, Ticket.reopen),
            (raul, Ticket.close),
        ],
        start=1,
    ):
        move(ticket, user, DEFAULT_TICKET_TIME + timedelta(hours=hours))
    db_session.commit()
    ticket_id = ticket.id

    with new_session(app) as session:
        with count_statements(session) as statements:
            found = SqlAlchemyTicketRepository(session).get_with_history(ticket_id)
            assert found is not None
            assert len(found.state_history) == 5
            assert {c.user.name for c in found.state_history} == {"Ana", "Raul"}

        assert len(statements) <= 8


def test_history_reads_return_none_for_non_participants_and_out_of_range_ids(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-37 · TC-TKT-37b"""
    ana = make_user("Client", name="Ana")
    beto = make_user("Client", name="Beto")
    raul = make_user("Representative", name="Raul")
    ticket = make_ticket(ana, raul)
    repository = SqlAlchemyTicketRepository(db_session)

    assert repository.get_visible_with_history(ticket.id, beto) is None
    assert repository.get_visible_with_history(2**63, ana) is None
    assert repository.get_with_history(2**63) is None


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


def test_search_by_client_returns_only_the_tickets_of_that_client(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-17 · TC-TKT-17b"""
    ana = make_user("Client", name="Ana")
    beto = make_user("Client", name="Beto")
    carla = make_user("Client", name="Carla")
    raul = make_user("Representative", name="Raul")
    anas = [make_ticket(ana, raul), make_ticket(ana, raul)]
    make_ticket(beto, raul)
    repository = SqlAlchemyTicketRepository(db_session)

    assert {ticket.id for ticket in repository.search(client_id=ana.id)} == {t.id for t in anas}
    assert repository.search(client_id=carla.id) == []


def test_search_by_representative_returns_only_the_tickets_assigned_to_them(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-18 · TC-TKT-18b"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    rosa = make_user("Representative", name="Rosa")
    rauls = [make_ticket(ana, raul), make_ticket(ana, raul)]
    make_ticket(ana, rosa)
    repository = SqlAlchemyTicketRepository(db_session)

    result = repository.search(representative_id=raul.id)

    assert {ticket.id for ticket in result} == {t.id for t in rauls}


def _walk_ticket_graph(tickets: list[Ticket]) -> None:
    for ticket in tickets:
        assert ticket.client.name
        assert ticket.representative.name
        for product in ticket.products:
            assert product.product_type.category.name


def test_search_by_client_loads_everything_in_few_statements(
    app: Flask,
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
) -> None:
    """SPEC-TKT-17 · TC-TKT-17c"""
    ana = make_user("Client", name="Ana")
    kinds = [
        make_product_type(make_category("Hardware"), "Notebook"),
        make_product_type(make_category("Software"), "Editor"),
    ]
    for index in range(3):
        representative = make_user("Representative", name=f"Rep {index}")
        products = [make_product(kind, f"{kind.name} {index}") for kind in kinds]
        make_ticket(ana, representative, products)
    ana_id = ana.id

    with new_session(app) as session:
        with count_statements(session) as statements:
            _walk_ticket_graph(SqlAlchemyTicketRepository(session).search(client_id=ana_id))

        assert len(statements) <= 6


def test_search_by_representative_loads_everything_in_few_statements(
    app: Flask,
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
) -> None:
    """SPEC-TKT-18 · TC-TKT-18c"""
    raul = make_user("Representative", name="Raul")
    kinds = [
        make_product_type(make_category("Hardware"), "Notebook"),
        make_product_type(make_category("Software"), "Editor"),
    ]
    for index in range(3):
        client = make_user("Client", name=f"Client {index}")
        products = [make_product(kind, f"{kind.name} {index}") for kind in kinds]
        make_ticket(client, raul, products)
    raul_id = raul.id

    with new_session(app) as session:
        with count_statements(session) as statements:
            _walk_ticket_graph(
                SqlAlchemyTicketRepository(session).search(representative_id=raul_id)
            )

        assert len(statements) <= 6


def test_search_with_text_and_window_loads_everything_in_few_statements(
    app: Flask,
    db_session: Session,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
    make_ticket: MakeTicket,
) -> None:
    """SPEC-TKT-45 · TC-TKT-45g"""
    ana = make_user("Client", name="Ana")
    kinds = [
        make_product_type(make_category("Hardware"), "Notebook"),
        make_product_type(make_category("Software"), "Editor"),
    ]
    for index in range(3):
        representative = make_user("Representative", name=f"Rep {index}")
        products = [make_product(kind, f"{kind.name} {index}") for kind in kinds]
        make_ticket(ana, representative, products)

    with new_session(app) as session:
        repository = SqlAlchemyTicketRepository(session)
        with count_statements(session) as statements:
            _walk_ticket_graph(repository.search(q="ana"))

        assert len(statements) <= 6

        with count_statements(session) as statements:
            page = repository.search(window=PageRequest(1, 2))
            assert isinstance(page, Page)
            _walk_ticket_graph(list(page.items))

        assert len(statements) <= 7


def test_search_by_representative_orders_newest_first_with_id_descending_on_ties(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-29 · TC-TKT-29b"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    older = make_ticket(ana, raul, now=DEFAULT_TICKET_TIME - timedelta(hours=1))
    tied = [make_ticket(ana, raul) for _ in range(3)]

    result = SqlAlchemyTicketRepository(db_session).search(representative_id=raul.id)

    assert [t.id for t in result] == [*sorted((t.id for t in tied), reverse=True), older.id]


def test_search_by_client_orders_newest_first_with_id_descending_on_ties(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
) -> None:
    """SPEC-TKT-29 · TC-TKT-29b"""
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    older = make_ticket(ana, raul, now=DEFAULT_TICKET_TIME - timedelta(hours=1))
    tied = [make_ticket(ana, raul) for _ in range(3)]

    result = SqlAlchemyTicketRepository(db_session).search(client_id=ana.id)

    assert [t.id for t in result] == [*sorted((t.id for t in tied), reverse=True), older.id]


class ListingData(NamedTuple):
    ana: User
    beto: User
    angela: User
    raul: User
    rosa: User
    t1: Ticket
    t2: Ticket
    t3: Ticket
    t4: Ticket


@pytest.fixture
def listing_data(db_session: Session, make_user: MakeUser, make_ticket: MakeTicket) -> ListingData:
    ana = make_user("Client", name="Ana")
    beto = make_user("Client", name="Beto")
    angela = make_user("Client", name="Ángela")
    raul = make_user("Representative", name="Raúl")
    rosa = make_user("Representative", name="Rosa")
    t0 = DEFAULT_TICKET_TIME
    t1 = make_ticket(ana, raul, first_message="Hola, no anda el router", now=t0)
    t2 = make_ticket(beto, raul, first_message="Pedido 50% off", now=t0 + timedelta(hours=1))
    t3 = make_ticket(ana, rosa, first_message="Factura", now=t0 + timedelta(hours=2))
    t4 = make_ticket(angela, rosa, first_message="Router roto", now=t0 + timedelta(hours=2))
    t2.close(beto, t0 + timedelta(hours=3))
    t3.start_progress(rosa, t0 + timedelta(hours=3))
    t3.add_milestone("router nuevo", rosa, t0 + timedelta(hours=4))
    db_session.commit()
    return ListingData(ana, beto, angela, raul, rosa, t1, t2, t3, t4)


def ids(tickets: Iterable[Ticket]) -> list[int]:
    return [ticket.id for ticket in tickets]


def test_search_without_filters_returns_every_ticket_newest_first(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-33 · TC-TKT-33b"""
    d = listing_data

    result = SqlAlchemyTicketRepository(db_session).search()

    assert ids(result) == ids([d.t4, d.t3, d.t2, d.t1])


def test_search_filters_by_state(db_session: Session, listing_data: ListingData) -> None:
    """SPEC-TKT-38 · TC-TKT-38b"""
    d = listing_data

    result = SqlAlchemyTicketRepository(db_session).search(state="New")

    assert ids(result) == ids([d.t4, d.t1])


def test_search_filters_by_client_and_combines_filters_with_and(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-39 · TC-TKT-39b"""
    d = listing_data
    repository = SqlAlchemyTicketRepository(db_session)

    assert ids(repository.search(client_id=d.ana.id)) == ids([d.t3, d.t1])
    assert ids(repository.search(client_id=d.ana.id, representative_id=d.raul.id)) == ids([d.t1])


def test_search_with_an_id_that_does_not_fit_matches_nothing_without_querying(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-39 · TC-TKT-39c"""
    repository = SqlAlchemyTicketRepository(db_session)

    with count_statements(db_session) as statements:
        by_client = repository.search(client_id=2**63)
        page = repository.search(representative_id=2**63, window=PageRequest(1, 20))

    assert by_client == []
    assert page == Page(items=[], page=1, page_size=20, total=0)
    assert statements == []


def test_search_filters_by_representative(db_session: Session, listing_data: ListingData) -> None:
    """SPEC-TKT-40 · TC-TKT-40b"""
    d = listing_data

    result = SqlAlchemyTicketRepository(db_session).search(representative_id=d.rosa.id)

    assert ids(result) == ids([d.t4, d.t3])


def test_search_orders_ascending_with_the_id_tie_break_in_the_same_direction(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-42 · TC-TKT-42b"""
    d = listing_data
    repository = SqlAlchemyTicketRepository(db_session)

    assert ids(repository.search(ascending=True)) == ids([d.t1, d.t2, d.t3, d.t4])
    assert ids(repository.search()) == ids([d.t4, d.t3, d.t2, d.t1])


def test_search_combines_representative_and_state_with_and(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-44 · TC-TKT-44b"""
    d = listing_data

    result = SqlAlchemyTicketRepository(db_session).search(representative_id=d.raul.id, state="New")

    assert ids(result) == ids([d.t1])


@pytest.mark.parametrize("ascending", [False, True])
def test_search_pages_concatenate_to_the_full_listing_without_overlaps(
    db_session: Session,
    make_user: MakeUser,
    make_ticket: MakeTicket,
    listing_data: ListingData,
    ascending: bool,
) -> None:
    """SPEC-TKT-45 · TC-TKT-45e"""
    d = listing_data
    for _ in range(2):
        make_ticket(d.ana, d.rosa, now=DEFAULT_TICKET_TIME + timedelta(hours=2))
    repository = SqlAlchemyTicketRepository(db_session)
    everything = ids(repository.search(ascending=ascending))

    pages = [repository.search(ascending=ascending, window=PageRequest(p, 2)) for p in (1, 2, 3, 4)]

    assert [page.total for page in pages] == [6, 6, 6, 6]
    assert [i for page in pages for i in ids(page.items)] == everything
    assert len(everything) == 6


def test_search_text_matches_the_client_name_or_the_first_message_ignoring_case(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-41 · TC-TKT-41b"""
    d = listing_data
    repository = SqlAlchemyTicketRepository(db_session)

    assert ids(repository.search(q="ÁNGELA")) == ids([d.t4])
    assert ids(repository.search(q="router")) == ids([d.t4, d.t1])


def test_search_text_treats_percent_and_underscore_literally(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-41 · TC-TKT-41c"""
    d = listing_data
    repository = SqlAlchemyTicketRepository(db_session)

    assert ids(repository.search(q="%")) == ids([d.t2])
    assert repository.search(q="_") == []


def test_search_text_looks_only_at_the_first_message(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-41 · TC-TKT-41d"""
    result = SqlAlchemyTicketRepository(db_session).search(q="nuevo")

    assert result == []


def test_search_text_combines_with_the_other_filters_with_and(
    db_session: Session, listing_data: ListingData
) -> None:
    """SPEC-TKT-44 · TC-TKT-44b"""
    d = listing_data

    result = SqlAlchemyTicketRepository(db_session).search(
        representative_id=d.raul.id, q="router", state="New"
    )

    assert ids(result) == ids([d.t1])
