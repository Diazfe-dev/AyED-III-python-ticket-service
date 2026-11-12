from types import SimpleNamespace

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.domain.ticket import Ticket
from tests.conftest import LoginAs
from tests.integration.notifications.conftest import notification_rows


def test_rejected_operations_add_no_notification(
    client: FlaskClient,
    login_as: LoginAs,
    admin_client: FlaskClient,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-NTF-15 · TC-NTF-15b"""
    ticket_url = f"/tickets/{world.ticket.id}"
    checked: list[tuple[int, int]] = []

    def expect(status: int, response) -> None:
        checked.append((status, response.status_code))
        assert len(notification_rows(db_session)) == rows_before

    rows_before = 0
    anonymous = client.application.test_client()
    expect(401, anonymous.post(f"{ticket_url}/close"))
    expect(
        403, admin_client.post("/tickets", json={"client_id": world.ana.id, "first_message": "x"})
    )
    expect(403, admin_client.post(f"{ticket_url}/close"))

    login_as(client, world.ana)
    expect(403, client.post("/tickets", json={"client_id": world.ana.id, "first_message": "x"}))

    login_as(client, world.raul)
    expect(400, client.post(f"{ticket_url}/milestones", json={"content": ""}))
    expect(404, client.post("/tickets/9999/close"))
    expect(409, client.post(f"{ticket_url}/reopen"))

    assert client.post(f"{ticket_url}/close").status_code == 200
    rows_before = len(notification_rows(db_session))
    expect(409, client.post(f"{ticket_url}/milestones", json={"content": "Tarde"}))

    assert [e for e, _ in checked] == [a for _, a in checked]


def test_a_failing_commit_answers_500_and_notifies_nobody(
    app: Flask,
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPEC-NTF-15 · TC-NTF-15e"""
    app.config["PROPAGATE_EXCEPTIONS"] = False
    login_as(client, world.raul)

    def failing_commit(self: Session) -> None:
        raise RuntimeError("commit failed")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", failing_commit)
        response = client.post(f"/tickets/{world.ticket.id}/close")

    assert response.status_code == 500
    assert response.get_json() == {"error": "internal_error"}
    db_session.expire_all()
    assert db_session.get_one(Ticket, world.ticket.id).state_name == "New"
    assert notification_rows(db_session) == []
