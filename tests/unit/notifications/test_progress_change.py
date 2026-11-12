from datetime import UTC, datetime, timedelta

from app.domain.ticket import Ticket
from app.domain.users import Client, Representative

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T1 + timedelta(hours=1)


def test_request_progress_reports_whether_the_state_changed():
    """SPEC-NTF-08 · TC-NTF-08a"""
    raul = Representative(name="Raul")
    ticket = Ticket.open(Client(name="Ana"), raul, [], "Hola", T0)

    first = ticket.request_progress(raul, T1)
    second = ticket.request_progress(raul, T2)

    assert first is True
    assert second is False
    assert ticket.state_name == "InProgress"
