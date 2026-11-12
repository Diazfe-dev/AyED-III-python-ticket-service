from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.milestone import Milestone
from app.domain.ticket import Ticket
from tests.conftest import DEFAULT_TICKET_TIME

T1 = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
T2 = T1 + timedelta(hours=1)


def _reload(db_session: Session, ticket_id: int) -> Ticket:
    db_session.expunge_all()
    return db_session.get_one(Ticket, ticket_id)


def test_added_milestone_is_stored_with_author_content_and_instant(
    db_session: Session, world: SimpleNamespace
):
    """SPEC-MLS-03 · TC-MLS-03b"""
    ticket_id = world.ticket.id
    raul_id = world.raul.id
    world.ticket.add_milestone("Revisando", world.raul, T1)
    db_session.commit()

    row = db_session.scalars(select(Milestone).where(Milestone.content == "Revisando")).one()
    db_session.expunge_all()
    row = db_session.get_one(Milestone, row.id)

    assert row.ticket_id == ticket_id
    assert row.author_id == raul_id
    assert row.created_at == T1
    assert row.created_at.tzinfo is UTC


def test_milestones_are_ordered_by_instant_then_id(db_session: Session, world: SimpleNamespace):
    """SPEC-MLS-07 · TC-MLS-07b"""
    ticket_id = world.ticket.id
    world.ticket.add_milestone("B", world.raul, T2)
    world.ticket.add_milestone("C", world.ana, T1)
    world.ticket.add_milestone("D", world.raul, T2)
    db_session.commit()

    ticket = _reload(db_session, ticket_id)

    assert [m.content for m in ticket.milestones] == ["Hola", "C", "B", "D"]
    assert ticket.milestones[0].created_at == DEFAULT_TICKET_TIME
