from datetime import UTC, datetime, timedelta

import pytest

from app.domain.errors import InvalidTransitionError, ProductNotInTicketError
from app.domain.products import Product
from app.domain.states import NewState
from app.domain.ticket import Ticket
from app.domain.users import Client, Representative

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def make_parties() -> tuple[Client, Representative]:
    return Client(name="Ana"), Representative(name="Raul")


def test_open_associates_the_ticket_with_its_client_and_products():
    """SPEC-TKT-01 · TC-TKT-01a"""
    ana, raul = make_parties()
    xps = Product(name="XPS 13")

    ticket = Ticket.open(ana, raul, [xps], "Hola", NOW)

    assert ticket.client is ana
    assert ticket in ana.tickets
    assert ticket.products == [xps]


def test_open_assigns_the_creating_representative():
    """SPEC-TKT-02 · TC-TKT-02a"""
    ana, raul = make_parties()

    ticket = Ticket.open(ana, raul, [], "Hola", NOW)

    assert ticket.representative is raul
    assert ticket in raul.assigned_tickets


def test_open_leaves_the_ticket_in_new_state():
    """SPEC-TKT-03 · TC-TKT-03a"""
    ana, raul = make_parties()

    ticket = Ticket.open(ana, raul, [], "Hola", NOW)

    assert ticket.state_name == "New"
    assert isinstance(ticket.state, NewState)


def test_open_registers_the_first_message_as_the_initial_milestone():
    """SPEC-TKT-04 · TC-TKT-04a"""
    ana, raul = make_parties()

    ticket = Ticket.open(ana, raul, [], "Hola", NOW)

    assert len(ticket.milestones) == 1
    milestone = ticket.milestones[0]
    assert milestone.content == "Hola"
    assert milestone.author is raul
    assert milestone.created_at == NOW


def test_open_registers_the_initial_state_change_by_the_representative():
    """SPEC-TKT-15 · TC-TKT-15a"""
    ana, raul = make_parties()

    ticket = Ticket.open(ana, raul, [], "Hola", NOW)

    assert len(ticket.state_history) == 1
    change = ticket.state_history[0]
    assert change.state_name == "New"
    assert change.user is raul
    assert change.timestamp == NOW


def test_open_associates_every_given_product_once():
    """SPEC-TKT-31 · TC-TKT-31a"""
    ana, raul = make_parties()
    xps, desktop = Product(name="XPS 13"), Product(name="Desktop")

    ticket = Ticket.open(ana, raul, [xps, desktop], "Hola", NOW)

    assert sorted(p.name for p in ticket.products) == ["Desktop", "XPS 13"]
    assert len(ticket.products) == 2


def test_start_progress_moves_a_new_ticket_to_in_progress_and_records_it():
    """SPEC-TKT-09 · TC-TKT-09a"""
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [], "Hola", NOW)
    later = NOW + timedelta(seconds=30)

    ticket.start_progress(raul, later)

    assert ticket.state_name == "InProgress"
    change = ticket.state_history[-1]
    assert (change.state_name, change.user, change.timestamp) == ("InProgress", raul, later)


def test_new_ticket_can_be_closed():
    """SPEC-TKT-10 · TC-TKT-10a"""
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [], "Hola", NOW)

    ticket.close(ana, NOW)

    assert ticket.state_name == "Closed"


def test_in_progress_ticket_can_be_closed():
    """SPEC-TKT-10 · TC-TKT-10b"""
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [], "Hola", NOW)
    ticket.start_progress(raul, NOW)

    ticket.close(raul, NOW)

    assert ticket.state_name == "Closed"


def test_closing_records_who_closed_which_state_and_when():
    """SPEC-TKT-14 · TC-TKT-14a"""
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [], "Hola", NOW)
    before = len(ticket.state_history)
    closed_at = NOW + timedelta(hours=1)

    ticket.close(ana, closed_at)

    assert len(ticket.state_history) == before + 1
    change = ticket.state_history[-1]
    assert change.user is ana
    assert change.state_name == "Closed"
    assert change.timestamp == closed_at


def test_every_transition_adds_a_state_change_in_order():
    """SPEC-TKT-14 · TC-TKT-14b"""
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [], "Hola", NOW)
    t1, t2 = NOW + timedelta(minutes=1), NOW + timedelta(minutes=2)

    t3 = NOW + timedelta(minutes=3)

    ticket.start_progress(raul, t1)
    ticket.close(ana, t2)
    ticket.reopen(raul, t3)

    assert [(c.state_name, c.user, c.timestamp) for c in ticket.state_history] == [
        ("New", raul, NOW),
        ("InProgress", raul, t1),
        ("Closed", ana, t2),
        ("InProgress", raul, t3),
    ]


def test_reopened_ticket_goes_straight_to_in_progress():
    """SPEC-TKT-11 · TC-TKT-11a"""
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [], "Hola", NOW)
    ticket.close(ana, NOW)

    ticket.reopen(ana, NOW)

    assert ticket.state_name == "InProgress"


def test_reopening_keeps_the_same_representative():
    """SPEC-TKT-12 · TC-TKT-12a"""
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [], "Hola", NOW)
    representative_id = ticket.representative_id

    for actor in (ana, raul):
        ticket.close(actor, NOW)
        ticket.reopen(actor, NOW)

    assert ticket.representative is raul
    assert ticket.representative_id == representative_id


def _ticket_in(state_name: str) -> tuple[Ticket, Client, Representative]:
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [Product(name="XPS 13")], "Hola", NOW)
    if state_name == "InProgress":
        ticket.start_progress(raul, NOW)
    if state_name == "Closed":
        ticket.close(ana, NOW)
    return ticket, ana, raul


DISALLOWED_TRANSITIONS = [
    ("New", "reopen"),
    ("InProgress", "start_progress"),
    ("InProgress", "reopen"),
    ("Closed", "close"),
    ("Closed", "start_progress"),
]


@pytest.mark.parametrize(("state_name", "transition"), DISALLOWED_TRANSITIONS)
def test_transition_not_allowed_by_the_state_is_rejected(state_name: str, transition: str):
    """SPEC-TKT-13 · TC-TKT-13a"""
    ticket, ana, _ = _ticket_in(state_name)

    with pytest.raises(InvalidTransitionError):
        getattr(ticket, transition)(ana, NOW)


@pytest.mark.parametrize(("state_name", "transition"), DISALLOWED_TRANSITIONS)
def test_rejected_transition_leaves_the_ticket_unchanged(state_name: str, transition: str):
    """SPEC-TKT-13 · TC-TKT-13b"""
    ticket, ana, _ = _ticket_in(state_name)
    history = list(ticket.state_history)
    milestones = list(ticket.milestones)
    products = list(ticket.products)

    with pytest.raises(InvalidTransitionError):
        getattr(ticket, transition)(ana, NOW + timedelta(hours=1))

    assert ticket.state_name == state_name
    assert ticket.state_history == history
    assert ticket.milestones == milestones
    assert ticket.products == products


def test_add_products_associates_each_product_with_the_ticket():
    """SPEC-TKT-07 · TC-TKT-07a"""
    ana, raul = make_parties()
    ticket = Ticket.open(ana, raul, [], "Hola", NOW)
    xps, desktop = Product(name="XPS 13"), Product(name="Desktop")

    ticket.add_products([xps, desktop])

    assert ticket.products == [xps, desktop]


def test_add_products_ignores_the_ones_already_associated():
    """SPEC-TKT-25 · TC-TKT-25a"""
    ana, raul = make_parties()
    xps = Product(name="XPS 13")
    ticket = Ticket.open(ana, raul, [xps], "Hola", NOW)

    ticket.add_products([xps])

    assert ticket.products == [xps]


def test_remove_product_drops_only_the_association():
    """SPEC-TKT-21 · TC-TKT-21a"""
    ana, raul = make_parties()
    xps, optiplex = Product(name="XPS 13"), Product(name="Optiplex")
    ticket = Ticket.open(ana, raul, [xps, optiplex], "Hola", NOW)

    ticket.remove_product(xps)

    assert ticket.products == [optiplex]
    assert xps.name == "XPS 13"


def test_remove_product_that_is_not_associated_is_rejected():
    """SPEC-TKT-26 · TC-TKT-26a"""
    ana, raul = make_parties()
    xps, desktop = Product(name="XPS 13"), Product(name="Desktop")
    ticket = Ticket.open(ana, raul, [xps], "Hola", NOW)

    with pytest.raises(ProductNotInTicketError):
        ticket.remove_product(desktop)

    assert ticket.products == [xps]
