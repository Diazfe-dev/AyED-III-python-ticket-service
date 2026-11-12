from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.notifications import Notification
from app.domain.ticket import Ticket
from tests.conftest import MakeTicket, MakeUser
from tests.integration.tickets.test_schema_registration import run_fresh

T1 = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
T2 = T1 + timedelta(hours=1)


@pytest.fixture
def world(make_user: MakeUser, make_ticket: MakeTicket) -> SimpleNamespace:
    ana = make_user("Client", name="Ana")
    raul = make_user("Representative", name="Raul")
    return SimpleNamespace(ana=ana, raul=raul, ticket=make_ticket(ana, raul))


def test_sent_and_failed_notifications_are_stored(db_session: Session, world: SimpleNamespace):
    """SPEC-NTF-03 · TC-NTF-03d"""
    ticket_id, ana_id, raul_id = world.ticket.id, world.ana.id, world.raul.id
    world.ticket.record_notification(world.ana, "mail", "m", T1)
    world.ticket.record_failed_notification(world.raul, "mail", "m2", T2, "boom")
    db_session.commit()
    db_session.expunge_all()

    ticket = db_session.get_one(Ticket, ticket_id)
    first, second = ticket.notifications

    assert (first.ticket_id, first.recipient_id) == (ticket_id, ana_id)
    assert (first.channel, first.message, first.status, first.error) == ("mail", "m", "sent", None)
    assert first.created_at == T1
    assert first.created_at.tzinfo is UTC
    assert (second.ticket_id, second.recipient_id) == (ticket_id, raul_id)
    assert (second.message, second.status, second.error) == ("m2", "failed", "boom")
    assert second.created_at == T2


def test_notifications_are_ordered_by_instant_then_id(db_session: Session, world: SimpleNamespace):
    """SPEC-NTF-03 · TC-NTF-03d"""
    ticket_id = world.ticket.id
    world.ticket.record_notification(world.ana, "mail", "B", T2)
    world.ticket.record_notification(world.ana, "mail", "C", T1)
    world.ticket.record_notification(world.ana, "mail", "D", T2)
    db_session.commit()
    db_session.expunge_all()

    ticket = db_session.get_one(Ticket, ticket_id)

    assert [n.message for n in ticket.notifications] == ["C", "B", "D"]


def test_notifications_table_exists_in_a_fresh_interpreter():
    """SPEC-NTF-03 · TC-NTF-03e"""
    script = """
with engine.connect() as conn:
    rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'")).scalars()
    print(" ".join(rows))
"""
    result = run_fresh(script)

    assert result.returncode == 0, result.stderr
    assert "notifications" in result.stdout.split()


def test_status_outside_sent_and_failed_is_rejected(db_session: Session, world: SimpleNamespace):
    """SPEC-NTF-03 · TC-NTF-03f"""
    statement = text(
        "INSERT INTO notifications (ticket_id, recipient_id, channel, message, created_at, status)"
        " VALUES (:ticket_id, :recipient_id, 'mail', 'm', '2026-02-01 09:00:00', :status)"
    )

    with pytest.raises(IntegrityError):
        db_session.execute(
            statement,
            {"ticket_id": world.ticket.id, "recipient_id": world.ana.id, "status": "pending"},
        )
    db_session.rollback()

    assert db_session.scalars(select(Notification)).all() == []
