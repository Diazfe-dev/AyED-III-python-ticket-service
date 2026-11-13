from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.milestone import Milestone
from app.domain.state_change import StateChange
from app.domain.ticket import Ticket
from app.domain.users import User
from app.repositories.ticket_repository import SqlAlchemyTicketRepository
from tests.conftest import LoginAs


def counts(db_session: Session) -> tuple[int, int]:
    db_session.expire_all()
    milestones = db_session.scalar(select(func.count()).select_from(Milestone)) or 0
    changes = db_session.scalar(select(func.count()).select_from(StateChange)) or 0
    return milestones, changes


def state_of(db_session: Session, ticket_id: int) -> str:
    db_session.expire_all()
    return db_session.get_one(Ticket, ticket_id).state_name


def milestones_url(world: SimpleNamespace) -> str:
    return f"/tickets/{world.ticket.id}/milestones"


def test_the_representative_registers_a_milestone(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-01 · TC-MLS-01f"""
    login_as(client, world.raul)
    before = counts(db_session)

    response = client.post(milestones_url(world), json={"content": "Revisando"})

    assert response.status_code == 201
    body = response.get_json()
    assert body == {
        "id": body["id"],
        "content": "Revisando",
        "author": {"id": world.raul.id, "name": "Raul", "role": "Representative"},
        "created_at": body["created_at"],
    }
    assert isinstance(body["id"], int)
    assert datetime.fromisoformat(body["created_at"]).utcoffset().total_seconds() == 0
    assert counts(db_session) == (before[0] + 1, before[1])
    assert state_of(db_session, world.ticket.id) == "New"


def test_start_progress_is_ignored_when_the_ticket_is_in_progress(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-01 · TC-MLS-01g"""
    login_as(client, world.raul)
    assert client.post(milestones_url(world), json={"content": "Hola", "start_progress": True})
    changes = counts(db_session)[1]

    response = client.post(milestones_url(world), json={"content": "Sigo", "start_progress": True})

    assert response.status_code == 201
    assert state_of(db_session, world.ticket.id) == "InProgress"
    assert counts(db_session)[1] == changes


@pytest.mark.parametrize("content", ["x" * 20000, "  Hola  "])
def test_the_content_is_stored_as_it_arrives(
    content: str,
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-MLS-01 · TC-MLS-01h"""
    login_as(client, world.raul)

    response = client.post(milestones_url(world), json={"content": content})

    assert response.status_code == 201
    assert response.get_json()["content"] == content
    stored = db_session.get_one(Milestone, response.get_json()["id"])
    assert stored.content == content


def test_the_client_registers_a_milestone(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-02 · TC-MLS-02d"""
    login_as(client, world.ana)
    before = counts(db_session)

    response = client.post(milestones_url(world), json={"content": "Gracias"})

    assert response.status_code == 201
    assert response.get_json()["author"] == {"id": world.ana.id, "name": "Ana", "role": "Client"}
    assert counts(db_session)[0] == before[0] + 1


def test_the_client_cannot_start_progress(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-02 · TC-MLS-02e"""
    login_as(client, world.ana)
    changes = counts(db_session)[1]

    response = client.post(
        milestones_url(world), json={"content": "Gracias", "start_progress": True}
    )

    assert response.status_code == 201
    assert client.get(f"/tickets/{world.ticket.id}").get_json()["state"] == "New"
    assert counts(db_session)[1] == changes


def test_the_author_and_the_date_come_from_the_session_and_the_clock(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-03 · TC-MLS-03d"""
    login_as(client, world.raul)

    response = client.post(
        milestones_url(world),
        json={"content": "Hola", "author_id": world.ana.id, "created_at": "2000-01-01T00:00:00Z"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["author"]["id"] == world.raul.id
    assert not body["created_at"].startswith("2000")
    stored = db_session.get_one(Milestone, body["id"])
    assert stored.author_id == world.raul.id
    assert stored.created_at.isoformat() == body["created_at"]
    assert body["created_at"].endswith("+00:00")


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"json": {}},
        {"json": {"content": ""}},
        {"json": {"content": "   "}},
        {"json": {"content": None}},
        {"json": ["Hola"]},
    ],
    ids=["no body", "empty object", "empty", "blank", "null", "list"],
)
def test_a_missing_or_blank_content_is_a_validation_error(
    kwargs: dict[str, Any],
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-MLS-04 · TC-MLS-04d"""
    login_as(client, world.raul)
    before = counts(db_session)

    response = client.post(milestones_url(world), **kwargs)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"content": "required"},
    }
    assert counts(db_session) == before


@pytest.mark.parametrize("content", [123, ["Hola"]])
def test_a_content_that_is_not_text_is_invalid(
    content: Any,
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-MLS-11 · TC-MLS-11b"""
    login_as(client, world.raul)
    before = counts(db_session)

    response = client.post(milestones_url(world), json={"content": content})

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "validation_error"
    assert body["fields"]["content"] == "invalid"
    assert counts(db_session) == before


def test_a_closed_ticket_rejects_milestones_and_start_progress(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-05 · TC-MLS-05e"""
    login_as(client, world.ana)
    assert client.post(f"/tickets/{world.ticket.id}/close").status_code == 200
    before = counts(db_session)

    own = client.post(milestones_url(world), json={"content": "Hola"})
    login_as(client, world.raul)
    assigned = client.post(milestones_url(world), json={"content": "Hola", "start_progress": True})

    for response in (own, assigned):
        assert response.status_code == 409
        assert response.get_json() == {"error": "ticket_closed"}
    assert counts(db_session) == before
    assert state_of(db_session, world.ticket.id) == "Closed"


def test_a_reopened_ticket_accepts_milestones_again(
    client: FlaskClient, login_as: LoginAs, world: SimpleNamespace
) -> None:
    """SPEC-MLS-05 · TC-MLS-05f"""
    login_as(client, world.ana)
    client.post(f"/tickets/{world.ticket.id}/close")
    assert client.post(milestones_url(world), json={"content": "Hola"}).status_code == 409
    assert client.post(f"/tickets/{world.ticket.id}/reopen").status_code == 200

    response = client.post(milestones_url(world), json={"content": "Hola"})

    assert response.status_code == 201


def test_start_progress_moves_the_ticket_in_the_same_operation(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-TKT-09 · TC-TKT-09b"""
    login_as(client, world.raul)

    response = client.post(
        milestones_url(world), json={"content": "Empiezo", "start_progress": True}
    )

    assert response.status_code == 201
    assert client.get(f"/tickets/{world.ticket.id}").get_json()["state"] == "InProgress"
    db_session.expire_all()
    change = db_session.scalars(
        select(StateChange)
        .where(StateChange.ticket_id == world.ticket.id)
        .order_by(StateChange.id.desc())
    ).first()
    assert change is not None
    assert (change.state_name, change.user_id) == ("InProgress", world.raul.id)
    milestone = db_session.get_one(Milestone, response.get_json()["id"])
    assert change.timestamp == milestone.created_at


@pytest.mark.parametrize("flag", [None, "yes", 1])
def test_a_start_progress_that_is_not_a_boolean_is_invalid(
    flag: Any,
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-TKT-09 · TC-TKT-09f"""
    login_as(client, world.raul)
    before = counts(db_session)

    response = client.post(milestones_url(world), json={"content": "Hola", "start_progress": flag})

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "validation_error"
    assert body["fields"]["start_progress"] == "invalid"
    assert counts(db_session) == before


def test_a_missing_start_progress_means_false(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-TKT-09 · TC-TKT-09f"""
    login_as(client, world.raul)

    response = client.post(milestones_url(world), json={"content": "Hola"})

    assert response.status_code == 201
    assert state_of(db_session, world.ticket.id) == "New"


def test_both_participants_list_the_milestones_in_order(
    client: FlaskClient, login_as: LoginAs, world: SimpleNamespace
) -> None:
    """SPEC-MLS-07 · TC-MLS-07e"""
    login_as(client, world.ana)
    client.post(milestones_url(world), json={"content": "Uno"})
    login_as(client, world.raul)
    client.post(milestones_url(world), json={"content": "Dos"})

    for user in (world.raul, world.ana):
        login_as(client, user)
        response = client.get(milestones_url(world))

        assert response.status_code == 200
        assert [m["content"] for m in response.get_json()] == ["Hola", "Uno", "Dos"]


@pytest.mark.parametrize("query", ["?page=1&page_size=1", "?page=abc&page_size=0"])
def test_listing_milestones_ignores_the_paging_parameters(
    query: str, client: FlaskClient, login_as: LoginAs, world: SimpleNamespace
) -> None:
    """SPEC-MLS-13 · TC-MLS-13a"""
    login_as(client, world.ana)
    client.post(milestones_url(world), json={"content": "Uno"})
    client.post(milestones_url(world), json={"content": "Dos"})

    response = client.get(milestones_url(world) + query)

    assert response.status_code == 200
    assert [m["content"] for m in response.get_json()] == ["Hola", "Uno", "Dos"]


def test_a_closed_ticket_still_lists_its_milestones(
    client: FlaskClient, login_as: LoginAs, world: SimpleNamespace
) -> None:
    """SPEC-MLS-07 · TC-MLS-07f"""
    login_as(client, world.ana)
    assert client.post(f"/tickets/{world.ticket.id}/close").status_code == 200

    response = client.get(milestones_url(world))

    assert response.status_code == 200
    assert [m["content"] for m in response.get_json()] == ["Hola"]


def test_each_listed_milestone_has_exactly_the_documented_fields(
    client: FlaskClient, login_as: LoginAs, world: SimpleNamespace
) -> None:
    """SPEC-MLS-08 · TC-MLS-08b"""
    login_as(client, world.ana)
    client.post(milestones_url(world), json={"content": "Dos"})

    listed = client.get(milestones_url(world)).get_json()

    assert [item["author"]["role"] for item in listed] == ["Representative", "Client"]
    for item in listed:
        assert set(item) == {"id", "content", "author", "created_at"}
        assert set(item["author"]) == {"id", "name", "role"}
        assert datetime.fromisoformat(item["created_at"]).utcoffset().total_seconds() == 0


def test_a_deactivated_author_still_appears_in_the_listing(
    app: Flask,
    client: FlaskClient,
    login_as: LoginAs,
    admin: User,
    world: SimpleNamespace,
) -> None:
    """SPEC-MLS-08 · TC-MLS-08c"""
    login_as(client, world.ana)
    client.post(milestones_url(world), json={"content": "Gracias"})
    admin_client = app.test_client()
    login_as(admin_client, admin)
    assert admin_client.post(f"/users/{world.ana.id}/deactivate").status_code == 200
    login_as(client, world.raul)

    response = client.get(milestones_url(world))

    assert response.status_code == 200
    last = response.get_json()[-1]
    assert last["author"] == {"id": world.ana.id, "name": "Ana", "role": "Client"}


@pytest.mark.parametrize("method", ["PATCH", "PUT"])
def test_a_milestone_collection_cannot_be_modified_by_the_api(
    method: str,
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-MLS-09 · TC-MLS-09g"""
    login_as(client, world.raul)
    first = world.ticket.milestones[0]
    before = (first.id, first.content, counts(db_session))

    collection = client.open(milestones_url(world), method=method, json={"content": "otro"})
    item = client.patch(f"{milestones_url(world)}/{before[0]}", json={"content": "otro"})

    assert collection.status_code == 405
    assert collection.get_json() == {"error": "method_not_allowed"}
    assert item.status_code == 404
    assert item.get_json() == {"error": "not_found"}
    db_session.expire_all()
    assert db_session.get_one(Milestone, before[0]).content == before[1]
    assert counts(db_session) == before[2]


def test_there_is_no_way_to_modify_or_delete_milestones_in_the_repository_or_routes(
    app: Flask,
) -> None:
    """SPEC-MLS-09 · TC-MLS-09h"""
    public = [name for name in dir(SqlAlchemyTicketRepository) if not name.startswith("_")]
    methods = {
        method
        for rule in app.url_map.iter_rules()
        if "/milestones" in rule.rule
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }

    assert [name for name in public if name.startswith(("update", "delete", "remove"))] == []
    assert methods == {"GET", "POST"}


def test_a_milestone_cannot_be_deleted_by_the_api(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-MLS-10 · TC-MLS-10e"""
    login_as(client, world.raul)
    first_id = world.ticket.milestones[0].id
    before = counts(db_session)

    collection = client.delete(milestones_url(world))
    item = client.delete(f"{milestones_url(world)}/{first_id}")

    assert collection.status_code == 405
    assert collection.get_json() == {"error": "method_not_allowed"}
    assert item.status_code == 404
    assert item.get_json() == {"error": "not_found"}
    assert counts(db_session) == before
    assert db_session.get(Milestone, first_id) is not None
