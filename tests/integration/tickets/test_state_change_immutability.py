import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
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


def test_raw_update_is_rejected_by_the_trigger_and_leaves_the_row_untouched(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-16 · TC-TKT-16d"""
    ticket = _ticket_with_history(make_user, make_ticket)
    before = _stored_states(db_session)
    change_id = ticket.state_history[0].id

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(
            text("UPDATE state_changes SET state_name = :s WHERE id = :id"),
            {"s": "Closed", "id": change_id},
        )
    db_session.rollback()

    assert _stored_states(db_session) == before


def test_raw_delete_is_rejected_by_the_trigger_and_keeps_the_row(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-16 · TC-TKT-16e"""
    ticket = _ticket_with_history(make_user, make_ticket)
    before = _stored_states(db_session)
    change_id = ticket.state_history[0].id

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(text("DELETE FROM state_changes WHERE id = :id"), {"id": change_id})
    db_session.rollback()

    assert _stored_states(db_session) == before


def test_bulk_statements_are_rejected_by_the_triggers(
    db_session: Session, make_user: MakeUser, make_ticket: MakeTicket
):
    """SPEC-TKT-16 · TC-TKT-16f"""
    _ticket_with_history(make_user, make_ticket)
    before = _stored_states(db_session)

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(update(StateChange).values(state_name="Closed"))
    db_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(delete(StateChange))
    db_session.rollback()

    assert _stored_states(db_session) == before


def test_schema_creates_the_immutability_triggers(db_session: Session):
    """SPEC-TKT-16 · TC-TKT-16i"""
    rows = db_session.execute(
        text("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger'")
    ).all()

    assert {(row.name, row.tbl_name) for row in rows} >= {
        ("state_changes_no_update", "state_changes"),
        ("state_changes_no_delete", "state_changes"),
    }
