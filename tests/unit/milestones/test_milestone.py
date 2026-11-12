from datetime import UTC, datetime, timedelta

import pytest

from app.domain.errors import TicketClosedError
from app.domain.ticket import Ticket
from app.domain.users import Client, Representative

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T1 + timedelta(hours=1)
T3 = T2 + timedelta(hours=1)


@pytest.fixture
def parties() -> tuple[Client, Representative]:
    return Client(name="Ana"), Representative(name="Raul")


@pytest.fixture
def ticket(parties) -> Ticket:
    ana, raul = parties
    return Ticket.open(ana, raul, [], "Hola", T0)


def test_representative_milestone_is_appended_to_the_ticket(ticket, parties):
    """SPEC-MLS-01 · TC-MLS-01a"""
    _, raul = parties

    milestone = ticket.add_milestone("Revisando", raul, T1)

    assert len(ticket.milestones) == 2
    assert ticket.milestones[-1] is milestone
    assert milestone.content == "Revisando"
    assert milestone.author is raul


def test_client_milestone_is_appended_to_the_ticket(ticket, parties):
    """SPEC-MLS-02 · TC-MLS-02a"""
    ana, _ = parties

    milestone = ticket.add_milestone("Gracias", ana, T1)

    assert milestone in ticket.milestones
    assert milestone.author is ana


def test_milestone_stores_author_and_creation_instant(ticket, parties):
    """SPEC-MLS-03 · TC-MLS-03a"""
    _, raul = parties

    milestone = ticket.add_milestone("Revisando", raul, T1)

    assert milestone.created_at == T1
    assert milestone.created_at.tzinfo is UTC
    assert milestone.author is raul


def test_closed_ticket_rejects_milestones(ticket, parties):
    """SPEC-MLS-05 · TC-MLS-05a"""
    ana, raul = parties
    ticket.close(raul, T1)

    with pytest.raises(TicketClosedError):
        ticket.add_milestone("Hola", ana, T2)

    assert len(ticket.milestones) == 1


def test_reopened_ticket_accepts_milestones_again(ticket, parties):
    """SPEC-MLS-05 · TC-MLS-05b"""
    ana, raul = parties
    ticket.close(raul, T1)
    ticket.reopen(raul, T2)

    milestone = ticket.add_milestone("Hola", ana, T3)

    assert ticket.milestones[-1] is milestone


def test_request_progress_moves_a_new_ticket_to_in_progress(ticket, parties):
    """SPEC-TKT-09 · TC-TKT-09c"""
    _, raul = parties

    ticket.request_progress(raul, T1)

    assert ticket.state_name == "InProgress"
    change = ticket.state_history[-1]
    assert (change.user, change.state_name, change.timestamp) == (raul, "InProgress", T1)
    assert len(ticket.state_history) == 2


def test_request_progress_does_nothing_when_already_in_progress(ticket, parties):
    """SPEC-MLS-01 · TC-MLS-01c"""
    _, raul = parties
    ticket.start_progress(raul, T1)

    ticket.request_progress(raul, T2)

    assert ticket.state_name == "InProgress"
    assert len(ticket.state_history) == 2
