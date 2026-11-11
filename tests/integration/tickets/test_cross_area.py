import pytest
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.milestone import Milestone
from app.domain.state_change import StateChange
from app.domain.ticket import Ticket
from tests.conftest import LoginAs, MakeTicket, MakeUser


def count_rows(db_session: Session, model: type, ticket_id: int) -> int:
    db_session.expire_all()
    statement = select(func.count()).select_from(model).where(model.ticket_id == ticket_id)
    return db_session.scalar(statement) or 0


@pytest.mark.parametrize(
    ("deactivated_role", "party_key", "other_key"),
    [
        ("Client", "client", "representative"),
        ("Representative", "representative", "client"),
    ],
)
def test_ticket_of_a_deactivated_user_keeps_its_history_and_stays_readable(
    admin_client: FlaskClient,
    db_session: Session,
    make_user: MakeUser,
    make_ticket: MakeTicket,
    login_as: LoginAs,
    deactivated_role: str,
    party_key: str,
    other_key: str,
) -> None:
    """SPEC-USR-10 · TC-USR-10d"""
    ana = make_user("Client", name="Ana", email="ana@x.com")
    raul = make_user("Representative", name="Raúl", email="raul@x.com")
    ticket_id = make_ticket(ana, raul).id
    deactivated, other = (ana, raul) if deactivated_role == "Client" else (raul, ana)
    deactivated_id, other_id, deactivated_email = deactivated.id, other.id, deactivated.email
    assert db_session.get(Ticket, ticket_id) is not None
    assert count_rows(db_session, Milestone, ticket_id) == 1
    assert count_rows(db_session, StateChange, ticket_id) == 1

    response = admin_client.post(f"/users/{deactivated_id}/deactivate")

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Ticket, ticket_id) is not None
    assert count_rows(db_session, Milestone, ticket_id) == 1
    assert count_rows(db_session, StateChange, ticket_id) == 1
    login_as(admin_client, other)
    read = admin_client.get(f"/tickets/{ticket_id}")
    assert read.status_code == 200
    assert read.get_json()[party_key]["id"] == deactivated_id
    assert read.get_json()[other_key]["id"] == other_id
    login = admin_client.post("/login", json={"email": deactivated_email, "password": "password1"})
    assert login.status_code == 401
