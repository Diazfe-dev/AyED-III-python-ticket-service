from types import SimpleNamespace
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app import create_app, wiring
from app.auth import USER_ID_KEY
from app.db import EXTENSION_KEY, create_schema, get_engine
from app.domain.base import Base
from app.domain.ticket import Ticket
from app.domain.users import Client, Representative
from tests.conftest import LoginAs
from tests.integration.notifications.conftest import notification_rows
from tests.unit.notifications.fakes import FailingStrategy


@pytest.fixture
def failing_strategies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        wiring,
        "notification_strategies",
        lambda: {"mail": FailingStrategy("SMTP down"), "whatsapp": FailingStrategy("SMTP down")},
    )


def test_a_failed_send_is_recorded_with_its_error(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
    failing_strategies: None,
) -> None:
    """SPEC-NTF-04 · TC-NTF-04c"""
    login_as(client, world.raul)

    response = client.post(f"/tickets/{world.ticket.id}/close")

    assert response.status_code == 200
    (row,) = notification_rows(db_session)
    assert (row.status, row.error, row.recipient_id) == ("failed", "SMTP down", world.ana.id)


def test_every_operation_persists_when_the_send_fails(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
    failing_strategies: None,
) -> None:
    """SPEC-NTF-14 · TC-NTF-14c"""
    login_as(client, world.raul)
    ticket_id = client.post(
        "/tickets", json={"client_id": world.ana.id, "first_message": "Hola"}
    ).get_json()["id"]
    client.post(f"/tickets/{ticket_id}/milestones", json={"content": "Revisando"})
    login_as(client, world.ana)
    client.post(f"/tickets/{ticket_id}/close")

    db_session.expire_all()
    ticket = db_session.get_one(Ticket, ticket_id)
    assert ticket.state_name == "Closed"
    assert ticket.state_history[-1].state_name == "Closed"
    assert [m.content for m in ticket.milestones][-1] == "Revisando"
    assert [row.status for row in notification_rows(db_session)] == ["failed"] * 3


def run_flow(app: Flask) -> list[tuple[int, Any]]:
    """Create the users in a fresh app, run the sequence of 14c and return its responses."""
    with app.app_context():
        create_schema(get_engine(), Base.metadata)
    session = app.extensions[EXTENSION_KEY]["session_factory"]()
    ana = Client(name="Ana", email="ana@x.com", password_hash="x", preferred_channel="mail")
    raul = Representative(
        name="Raul", email="raul@x.com", password_hash="x", preferred_channel="mail"
    )
    session.add_all([ana, raul])
    session.commit()
    ana_id, raul_id = ana.id, raul.id
    session.close()
    client = app.test_client()

    def login(user_id: int) -> None:
        with client.session_transaction() as http_session:
            http_session[USER_ID_KEY] = user_id

    login(raul_id)
    created = client.post("/tickets", json={"client_id": ana_id, "first_message": "Hola"})
    ticket_id = created.get_json()["id"]
    milestone = client.post(f"/tickets/{ticket_id}/milestones", json={"content": "Revisando"})
    login(ana_id)
    closed = client.post(f"/tickets/{ticket_id}/close")
    with app.app_context():
        get_engine().dispose()
    return [(r.status_code, without_dates(r.get_json())) for r in (created, milestone, closed)]


def without_dates(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: without_dates(v) for k, v in value.items() if not k.endswith("_at")}
    if isinstance(value, list):
        return [without_dates(item) for item in value]
    return value


def test_the_response_is_the_same_whether_the_send_fails_or_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPEC-NTF-19 · TC-NTF-19a"""
    normal = run_flow(create_app({"TESTING": True}))
    monkeypatch.setattr(
        wiring,
        "notification_strategies",
        lambda: {"mail": FailingStrategy("SMTP down"), "whatsapp": FailingStrategy("SMTP down")},
    )

    failing = run_flow(create_app({"TESTING": True}))

    assert [status for status, _ in normal] == [201, 201, 200]
    assert failing == normal
