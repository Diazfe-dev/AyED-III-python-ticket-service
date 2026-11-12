from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from flask import Flask
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.repositories.ticket_repository import SqlAlchemyTicketRepository
from tests.conftest import MakeTicket, MakeUser
from tests.integration.catalog.queries import count_statements

T1 = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
T2 = T1 + timedelta(hours=1)


def new_session(app: Flask) -> Session:
    return app.extensions[EXTENSION_KEY]["session_factory"]()


def test_get_visible_with_milestones_only_returns_the_ticket_to_participants(
    app: Flask, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-06 · TC-MLS-06a"""
    ticket_id = world.ticket.id
    with new_session(app) as session:
        repository = SqlAlchemyTicketRepository(session)
        users = {
            name: session.get_one(type(getattr(world, name)), getattr(world, name).id)
            for name in ("ana", "beto", "raul", "rosa")
        }

        assert repository.get_visible_with_milestones(ticket_id, users["beto"]) is None
        assert repository.get_visible_with_milestones(ticket_id, users["rosa"]) is None
        assert repository.get_visible_with_milestones(9999, users["ana"]) is None
        assert repository.get_visible_with_milestones(2**63, users["ana"]) is None
        for name in ("ana", "raul"):
            found = repository.get_visible_with_milestones(ticket_id, users[name])
            assert found is not None and found.id == ticket_id


def test_get_visible_with_milestones_keeps_the_chronological_order(
    app: Flask, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-07 · TC-MLS-07c"""
    ticket_id = world.ticket.id
    ana_id = world.ana.id
    world.ticket.add_milestone("B", world.raul, T2)
    world.ticket.add_milestone("C", world.ana, T1)
    world.ticket.add_milestone("D", world.raul, T2)
    db_session.commit()

    with new_session(app) as session:
        repository = SqlAlchemyTicketRepository(session)
        actor = session.get_one(type(world.ana), ana_id)
        ticket = repository.get_visible_with_milestones(ticket_id, actor)

        assert ticket is not None
        assert [m.content for m in ticket.milestones] == ["Hola", "C", "B", "D"]


def _statements_to_walk(app: Flask, ticket_id: int, actor_id: int, actor_type: type) -> int:
    with new_session(app) as session:
        actor = session.get_one(actor_type, actor_id)
        with count_statements(session) as statements:
            ticket = SqlAlchemyTicketRepository(session).get_visible_with_milestones(
                ticket_id, actor
            )
            assert ticket is not None
            for milestone in ticket.milestones:
                assert milestone.content
                assert milestone.author.name
                assert milestone.author.role
                assert milestone.created_at
        return len(statements)


def test_listing_milestones_does_not_grow_with_their_number(
    app: Flask,
    db_session: Session,
    world: SimpleNamespace,
    make_ticket: MakeTicket,
    make_user: MakeUser,
) -> None:
    """SPEC-MLS-08 · TC-MLS-08a"""
    big = make_ticket(world.ana, world.raul, [world.xps])
    authors = [world.ana, world.raul, world.beto, world.rosa, make_user("Client", name="Carla")]
    for index, author in enumerate(authors):
        big.add_milestone(f"M{index}", author, T1 + timedelta(minutes=index))
    world.ticket.add_milestone("Other", world.beto, T1)
    db_session.commit()
    small_id, big_id = world.ticket.id, big.id
    ana_id = world.ana.id

    small_count = _statements_to_walk(app, small_id, ana_id, type(world.ana))
    big_count = _statements_to_walk(app, big_id, ana_id, type(world.ana))

    assert small_count == big_count
    assert big_count <= 8
