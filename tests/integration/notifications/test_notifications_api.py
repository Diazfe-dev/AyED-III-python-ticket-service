from types import SimpleNamespace

from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.domain.ticket import Ticket
from tests.conftest import LoginAs, MakeProduct
from tests.integration.notifications.conftest import notification_rows


def test_creation_notifies_a_mail_recipient_through_mail(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-01 · TC-NTF-01c"""
    login_as(client, world.raul)

    response = client.post("/tickets", json={"client_id": world.ana.id, "first_message": "Hola"})

    assert response.status_code == 201
    (row,) = notification_rows(db_session)
    assert (row.recipient_id, row.channel) == (world.ana.id, "mail")


def test_creation_notifies_a_whatsapp_recipient_through_whatsapp(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-02 · TC-NTF-02c"""
    login_as(client, world.raul)

    response = client.post("/tickets", json={"client_id": world.wanda.id, "first_message": "Hola"})

    assert response.status_code == 201
    (row,) = notification_rows(db_session)
    assert (row.recipient_id, row.channel) == (world.wanda.id, "whatsapp")


def test_creation_records_exactly_one_notification_for_the_ticket(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-05 · TC-NTF-05b (dec. 4)"""
    login_as(client, world.raul)

    response = client.post("/tickets", json={"client_id": world.ana.id, "first_message": "Hola"})

    ticket_id = response.get_json()["id"]
    (row,) = notification_rows(db_session)
    assert response.status_code == 201
    assert row.ticket_id == ticket_id
    assert (row.recipient_id, row.status) == (world.ana.id, "sent")
    assert f"#{ticket_id}" in row.message
    assert "created" in row.message


def test_sending_is_recording_the_notification(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-12 · TC-NTF-12c"""
    login_as(client, world.raul)

    client.post("/tickets", json={"client_id": world.ana.id, "first_message": "Hola"})

    db_session.expire_all()
    (row,) = notification_rows(db_session)
    assert row.status == "sent"
    assert row.error is None


def post_milestone(client: FlaskClient, world: SimpleNamespace, **body: object):
    return client.post(f"/tickets/{world.ticket.id}/milestones", json=body)


def test_representative_milestone_notifies_the_client(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-06 · TC-NTF-06c"""
    login_as(client, world.raul)

    response = post_milestone(client, world, content="Revisando")

    assert response.status_code == 201
    (row,) = notification_rows(db_session)
    assert (row.recipient_id, row.status) == (world.ana.id, "sent")
    assert "milestone" in row.message


def test_representative_close_then_reopen_notify_the_client_in_order(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-07 · TC-NTF-07c"""
    login_as(client, world.raul)

    client.post(f"/tickets/{world.ticket.id}/close")
    client.post(f"/tickets/{world.ticket.id}/reopen")

    closed, reopened = notification_rows(db_session)
    assert (closed.recipient_id, reopened.recipient_id) == (world.ana.id, world.ana.id)
    assert "Closed" in closed.message
    assert "InProgress" in reopened.message


def test_milestone_that_starts_progress_sends_one_combined_notification(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-08 · TC-NTF-08c"""
    login_as(client, world.raul)

    response = post_milestone(client, world, content="Empiezo", start_progress=True)

    assert response.status_code == 201
    (row,) = notification_rows(db_session)
    assert row.recipient_id == world.ana.id
    assert "milestone" in row.message
    assert "InProgress" in row.message
    db_session.expire_all()
    assert db_session.get_one(Ticket, world.ticket.id).state_name == "InProgress"


def test_client_milestone_notifies_the_representative(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-09 · TC-NTF-09b"""
    login_as(client, world.ana)

    response = post_milestone(client, world, content="Gracias")

    assert response.status_code == 201
    (row,) = notification_rows(db_session)
    assert row.recipient_id == world.raul.id
    assert "milestone" in row.message


def test_client_reopen_notifies_the_representative(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-10 · TC-NTF-10b"""
    login_as(client, world.raul)
    client.post(f"/tickets/{world.ticket.id}/close")
    login_as(client, world.ana)

    response = client.post(f"/tickets/{world.ticket.id}/reopen")

    assert response.status_code == 200
    last = notification_rows(db_session)[-1]
    assert last.recipient_id == world.raul.id
    assert "reopened" in last.message


def test_client_close_notifies_the_representative(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-13 · TC-NTF-13b"""
    login_as(client, world.ana)

    response = client.post(f"/tickets/{world.ticket.id}/close")

    assert response.status_code == 200
    (row,) = notification_rows(db_session)
    assert row.recipient_id == world.raul.id
    assert "closed" in row.message


def test_an_inactive_client_is_still_notified(
    client: FlaskClient,
    login_as: LoginAs,
    admin_client: FlaskClient,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-NTF-16 · TC-NTF-16a (dec. 9)"""
    assert admin_client.post(f"/users/{world.ana.id}/deactivate").status_code == 200
    login_as(client, world.raul)

    response = post_milestone(client, world, content="Revisando")

    assert response.status_code == 201
    (row,) = notification_rows(db_session)
    assert (row.recipient_id, row.status) == (world.ana.id, "sent")


def test_an_inactive_representative_is_still_notified(
    client: FlaskClient,
    login_as: LoginAs,
    admin_client: FlaskClient,
    db_session: Session,
    world: SimpleNamespace,
) -> None:
    """SPEC-NTF-16 · TC-NTF-16b (dec. 9)"""
    assert admin_client.post(f"/users/{world.raul.id}/deactivate").status_code == 200
    login_as(client, world.ana)

    response = post_milestone(client, world, content="Gracias")

    assert response.status_code == 201
    (row,) = notification_rows(db_session)
    assert (row.recipient_id, row.status) == (world.raul.id, "sent")


def test_adding_and_removing_products_creates_no_notification(
    client: FlaskClient,
    login_as: LoginAs,
    db_session: Session,
    world: SimpleNamespace,
    make_product: MakeProduct,
) -> None:
    """SPEC-NTF-17 · TC-NTF-17b (dec. 12)"""
    login_as(client, world.raul)
    other = make_product(world.xps.product_type, "Other")

    added = client.post(f"/tickets/{world.ticket.id}/products", json={"product_ids": [other.id]})
    removed = client.delete(f"/tickets/{world.ticket.id}/products/{world.xps.id}")

    assert (added.status_code, removed.status_code) == (200, 204)
    assert notification_rows(db_session) == []


def test_messages_of_a_full_flow_identify_the_ticket_and_the_event(
    client: FlaskClient, login_as: LoginAs, db_session: Session, world: SimpleNamespace
) -> None:
    """SPEC-NTF-18 · TC-NTF-18b (dec. 10)"""
    login_as(client, world.raul)
    ticket_id = client.post(
        "/tickets", json={"client_id": world.ana.id, "first_message": "Hola"}
    ).get_json()["id"]
    base = f"/tickets/{ticket_id}"

    client.post(f"{base}/milestones", json={"content": "Revisando"})
    client.post(f"{base}/milestones", json={"content": "Empiezo", "start_progress": True})
    client.post(f"{base}/close")
    client.post(f"{base}/reopen")

    rows = notification_rows(db_session)
    expected = [
        ("created",),
        ("milestone",),
        ("milestone", "InProgress"),
        ("closed", "Closed"),
        ("reopened", "InProgress"),
    ]
    assert len(rows) == len(expected)
    for row, words in zip(rows, expected, strict=True):
        assert f"#{ticket_id}" in row.message
        assert all(word in row.message for word in words)
