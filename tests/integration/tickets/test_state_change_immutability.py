import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import ImmutableRecordError
from app.domain.state_change import StateChange
from app.domain.ticket import Ticket
from tests.conftest import MakeTicket, MakeUser
from tests.integration.catalog.queries import count_statements


def _ticket_with_history(make_user: MakeUser, make_ticket: MakeTicket) -> Ticket:
    return make_ticket(make_user("Client"), make_user("Representative"))


def _stored_states(session: Session) -> list[tuple[int, str]]:
    session.expire_all()
    rows = session.scalars(select(StateChange).order_by(StateChange.id))
    return [(row.ticket_id, row.state_name) for row in rows]


def test_modifying_a_state_change_raises_and_leaves_the_row_untouched(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-16 · TC-TKT-16a"""
    ticket = _ticket_with_history(make_user, make_ticket)
    before = _stored_states(db_session)
    change = ticket.state_history[0]

    change.state_name = "Closed"
    with pytest.raises(ImmutableRecordError):
        db_session.flush()
    db_session.rollback()

    assert _stored_states(db_session) == before


def test_deleting_a_state_change_raises_and_keeps_the_row(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-16 · TC-TKT-16b"""
    ticket = _ticket_with_history(make_user, make_ticket)
    before = _stored_states(db_session)

    db_session.delete(ticket.state_history[0])
    with pytest.raises(ImmutableRecordError):
        db_session.flush()
    db_session.rollback()

    assert _stored_states(db_session) == before


def test_removing_a_state_change_from_the_collection_raises_and_keeps_the_link(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-16 · TC-TKT-16c"""
    ticket = _ticket_with_history(make_user, make_ticket)
    before = _stored_states(db_session)

    ticket.state_history.remove(ticket.state_history[0])
    with pytest.raises(ImmutableRecordError):
        db_session.flush()
    db_session.rollback()

    assert _stored_states(db_session) == before


def test_listeners_stop_the_change_before_any_sql_runs(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-16 · TC-TKT-16h"""
    ticket = _ticket_with_history(make_user, make_ticket)
    change = ticket.state_history[0]

    with count_statements(db_session) as statements:
        change.state_name = "Closed"
        with pytest.raises(ImmutableRecordError):
            db_session.flush()
        db_session.rollback()
        db_session.delete(db_session.get(StateChange, change.id))
        with pytest.raises(ImmutableRecordError):
            db_session.flush()
        db_session.rollback()

    writes = [s for s in statements if s.lstrip().upper().startswith(("UPDATE", "DELETE"))]
    assert writes == []
