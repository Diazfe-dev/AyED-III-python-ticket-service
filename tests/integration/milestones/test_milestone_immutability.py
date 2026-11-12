from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.domain.errors import ImmutableRecordError
from app.domain.milestone import Milestone
from tests.integration.catalog.queries import count_statements
from tests.integration.tickets.test_schema_registration import run_fresh


def _stored(session: Session) -> list[tuple[int, int, str]]:
    session.expire_all()
    rows = session.scalars(select(Milestone).order_by(Milestone.id))
    return [(row.id, row.ticket_id, row.content) for row in rows]


def test_modifying_a_milestone_raises_and_leaves_the_row_untouched(
    db_session: Session, world: SimpleNamespace
):
    """SPEC-MLS-09 · TC-MLS-09a"""
    before = _stored(db_session)

    world.ticket.milestones[0].content = "otro"
    with pytest.raises(ImmutableRecordError):
        db_session.flush()
    db_session.rollback()

    assert _stored(db_session) == before


def test_listeners_stop_the_change_before_any_sql_runs(db_session: Session, world: SimpleNamespace):
    """SPEC-MLS-09 · TC-MLS-09b"""
    milestone = world.ticket.milestones[0]
    milestone_id = milestone.id

    with count_statements(db_session) as statements:
        milestone.content = "otro"
        with pytest.raises(ImmutableRecordError):
            db_session.flush()
        db_session.rollback()
        db_session.delete(db_session.get_one(Milestone, milestone_id))
        with pytest.raises(ImmutableRecordError):
            db_session.flush()
        db_session.rollback()

    writes = [s for s in statements if s.lstrip().upper().startswith(("UPDATE", "DELETE"))]
    assert writes == []


def test_raw_update_is_rejected_by_the_trigger(db_session: Session, world: SimpleNamespace):
    """SPEC-MLS-09 · TC-MLS-09c"""
    before = _stored(db_session)
    milestone_id = world.ticket.milestones[0].id

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(
            text("UPDATE milestones SET content = :c WHERE id = :id"),
            {"c": "otro", "id": milestone_id},
        )
    db_session.rollback()

    assert _stored(db_session) == before


def test_bulk_update_is_rejected_by_the_trigger(db_session: Session, world: SimpleNamespace):
    """SPEC-MLS-09 · TC-MLS-09d"""
    before = _stored(db_session)

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(update(Milestone).values(content="otro"))
    db_session.rollback()

    assert _stored(db_session) == before


def test_schema_creates_the_immutability_triggers(db_session: Session):
    """SPEC-MLS-09 · TC-MLS-09e"""
    rows = db_session.execute(
        text("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger'")
    ).all()

    assert {(row.name, row.tbl_name) for row in rows} >= {
        ("milestones_no_update", "milestones"),
        ("milestones_no_delete", "milestones"),
    }


def test_barriers_are_active_in_a_fresh_interpreter():
    """SPEC-MLS-09 · TC-MLS-09f"""
    script = """
from sqlalchemy import event
from app.domain.immutable import reject_delete, reject_update

with engine.connect() as conn:
    triggers = conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'trigger'")).scalars()
    print("TRIGGERS", " ".join(triggers))
cls = next(m.class_ for m in Base.registry.mappers if m.local_table.name == "milestones")
print("UPDATE", event.contains(cls, "before_update", reject_update))
print("DELETE", event.contains(cls, "before_delete", reject_delete))
"""
    result = run_fresh(script)

    assert result.returncode == 0, result.stderr
    assert "milestones_no_update" in result.stdout
    assert "milestones_no_delete" in result.stdout
    assert "UPDATE True" in result.stdout
    assert "DELETE True" in result.stdout


def test_deleting_a_milestone_raises_and_keeps_the_row(db_session: Session, world: SimpleNamespace):
    """SPEC-MLS-10 · TC-MLS-10a"""
    before = _stored(db_session)

    db_session.delete(world.ticket.milestones[0])
    with pytest.raises(ImmutableRecordError):
        db_session.flush()
    db_session.rollback()

    assert _stored(db_session) == before


def test_removing_a_milestone_from_the_collection_raises_and_keeps_the_link(
    db_session: Session, world: SimpleNamespace
):
    """SPEC-MLS-10 · TC-MLS-10b"""
    before = _stored(db_session)

    world.ticket.milestones.remove(world.ticket.milestones[0])
    with pytest.raises(ImmutableRecordError):
        db_session.flush()
    db_session.rollback()

    assert _stored(db_session) == before


def test_raw_delete_is_rejected_by_the_trigger(db_session: Session, world: SimpleNamespace):
    """SPEC-MLS-10 · TC-MLS-10c"""
    before = _stored(db_session)
    milestone_id = world.ticket.milestones[0].id

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(text("DELETE FROM milestones WHERE id = :id"), {"id": milestone_id})
    db_session.rollback()

    assert _stored(db_session) == before


def test_bulk_delete_is_rejected_by_the_trigger(db_session: Session, world: SimpleNamespace):
    """SPEC-MLS-10 · TC-MLS-10d"""
    before = _stored(db_session)

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(delete(Milestone))
    db_session.rollback()

    assert _stored(db_session) == before
