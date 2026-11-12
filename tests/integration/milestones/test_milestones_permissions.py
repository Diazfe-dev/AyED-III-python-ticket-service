from types import SimpleNamespace

import pytest
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.milestone import Milestone
from app.domain.state_change import StateChange
from tests.conftest import LoginAs

NOT_FOUND = {"error": "ticket_not_found"}


def counts(db_session: Session) -> list[int]:
    db_session.expire_all()
    return [
        db_session.scalar(select(func.count()).select_from(table)) or 0
        for table in (Milestone, StateChange)
    ]


@pytest.mark.parametrize(
    ("who", "ticket"),
    [
        ("raul", "own"),
        ("beto", "own"),
        ("rosa", "own"),
        ("raul", 9999),
        ("raul", 2**63),
    ],
)
def test_an_invalid_body_is_the_same_bad_request_for_every_ticket(
    who: str,
    ticket: str | int,
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-MLS-04 · TC-MLS-04e"""
    login_as(client, getattr(world, who))
    ticket_id = world.ticket.id if ticket == "own" else ticket
    before = counts(db_session)

    response = client.post(f"/tickets/{ticket_id}/milestones", json={"content": ""})

    assert response.status_code == 400
    assert response.get_json() == {"error": "validation_error", "fields": {"content": "required"}}
    assert counts(db_session) == before


def test_registering_on_a_foreign_ticket_answers_like_a_missing_one(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-06 · TC-MLS-06d"""
    before = counts(db_session)
    login_as(client, world.raul)
    missing = client.post("/tickets/9999/milestones", json={"content": "Hola"})
    out_of_range = client.post(f"/tickets/{2**63}/milestones", json={"content": "Hola"})

    for user in (world.beto, world.rosa):
        login_as(client, user)
        foreign = client.post(f"/tickets/{world.ticket.id}/milestones", json={"content": "Hola"})

        assert foreign.status_code == 404
        assert foreign.get_json() == NOT_FOUND
        assert foreign.get_json() == missing.get_json()
    assert missing.status_code == out_of_range.status_code == 404
    assert out_of_range.get_json() == NOT_FOUND
    assert counts(db_session) == before


def test_listing_a_foreign_ticket_answers_like_a_missing_one(
    client: FlaskClient, login_as: LoginAs, world: SimpleNamespace
) -> None:
    """SPEC-MLS-06 · TC-MLS-06e"""
    responses = []
    for user in (world.beto, world.rosa):
        login_as(client, user)
        responses.append(client.get(f"/tickets/{world.ticket.id}/milestones"))
    login_as(client, world.ana)
    responses.append(client.get("/tickets/9999/milestones"))
    responses.append(client.get(f"/tickets/{2**63}/milestones"))

    for response in responses:
        assert response.status_code == 404
        assert response.get_json() == NOT_FOUND


def test_the_admin_precedence_on_the_milestone_endpoints(
    admin_client: FlaskClient, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-TKT-27 · TC-TKT-27h"""
    before = counts(db_session)
    ticket_id = world.ticket.id

    missing_post = admin_client.post("/tickets/9999/milestones", json={"content": "Hola"})
    invalid_post = admin_client.post(f"/tickets/{ticket_id}/milestones", json={"content": ""})
    missing_get = admin_client.get("/tickets/9999/milestones")
    own_get = admin_client.get(f"/tickets/{ticket_id}/milestones")

    assert missing_post.status_code == 403
    assert missing_post.get_json() == {"error": "forbidden"}
    assert invalid_post.status_code == 400
    assert invalid_post.get_json() == {
        "error": "validation_error",
        "fields": {"content": "required"},
    }
    assert missing_get.status_code == own_get.status_code == 403
    assert missing_get.get_json() == own_get.get_json() == {"error": "forbidden"}
    assert counts(db_session) == before
