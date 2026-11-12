from datetime import UTC, datetime, timedelta

import pytest

from app.domain.notifications import Notification
from app.domain.ticket import Ticket
from app.domain.users import Client, Representative

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


@pytest.fixture
def parties() -> tuple[Client, Representative]:
    return Client(name="Ana"), Representative(name="Raul")


@pytest.fixture
def ticket(parties) -> Ticket:
    ana, raul = parties
    return Ticket.open(ana, raul, [], "Hola", T0)


def test_recorded_notification_is_appended_as_sent(ticket, parties):
    """SPEC-NTF-03 · TC-NTF-03a"""
    ana, _ = parties

    notification = ticket.record_notification(ana, "mail", "m", T1)

    assert isinstance(notification, Notification)
    assert ticket.notifications == [notification]
    assert notification.recipient is ana
    assert notification.channel == "mail"
    assert notification.message == "m"
    assert notification.created_at == T1
    assert notification.status == "sent"


def test_recorded_failed_notification_is_appended_as_failed(ticket, parties):
    """SPEC-NTF-03 · TC-NTF-03b"""
    ana, _ = parties

    notification = ticket.record_failed_notification(ana, "mail", "m", T1, "SMTP down")

    assert ticket.notifications == [notification]
    assert notification.recipient is ana
    assert notification.channel == "mail"
    assert notification.message == "m"
    assert notification.created_at == T1
    assert notification.status == "failed"


def test_failed_notification_keeps_the_error_and_sent_has_none(ticket, parties):
    """SPEC-NTF-04 · TC-NTF-04d"""
    ana, _ = parties

    failed = ticket.record_failed_notification(ana, "mail", "m", T1, "SMTP down")
    sent = ticket.record_notification(ana, "mail", "m", T1)

    assert failed.error == "SMTP down"
    assert sent.error is None
