from datetime import UTC, datetime

import pytest

from app.domain.ticket import Ticket
from app.domain.users import Client, Representative
from app.services.notification_service import NotificationService
from tests.unit.fakes import CommitSpy, FakeClock
from tests.unit.notifications.fakes import FailingStrategy, RecordingStrategy

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class Setup:
    def __init__(self) -> None:
        self.ana = Client(name="Ana", preferred_channel="mail")
        self.wanda = Client(name="Wanda", preferred_channel="whatsapp")
        self.raul = Representative(name="Raul", preferred_channel="mail")
        self.ticket = Ticket.open(self.ana, self.raul, [], "Hola", T0)
        self.mail = RecordingStrategy()
        self.whatsapp = RecordingStrategy()
        self.commit = CommitSpy()
        self.service = NotificationService(
            {"mail": self.mail, "whatsapp": self.whatsapp}, FakeClock(T0).now, self.commit
        )


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_mail_recipient_is_notified_with_the_mail_strategy(setup):
    """SPEC-NTF-01 · TC-NTF-01a"""
    setup.service.notify(setup.ana, setup.raul, setup.ticket, "m")

    assert setup.mail.sent == [(setup.ana, "m")]
    assert setup.whatsapp.sent == []
    assert setup.ticket.notifications[0].channel == "mail"


def test_whatsapp_recipient_is_notified_with_the_whatsapp_strategy(setup):
    """SPEC-NTF-02 · TC-NTF-02a"""
    setup.service.notify(setup.wanda, setup.raul, setup.ticket, "m")

    assert setup.whatsapp.sent == [(setup.wanda, "m")]
    assert setup.mail.sent == []
    assert setup.ticket.notifications[0].channel == "whatsapp"


def test_notify_records_a_sent_notification_and_commits_once(setup):
    """SPEC-NTF-03 · TC-NTF-03c"""
    setup.service.notify(setup.ana, setup.raul, setup.ticket, "m")

    (notification,) = setup.ticket.notifications
    assert notification.recipient is setup.ana
    assert notification.created_at == T0
    assert notification.channel == setup.ana.preferred_channel
    assert notification.message == "m"
    assert notification.status == "sent"
    assert setup.commit.calls == 1


def test_inactive_recipient_is_notified_anyway(setup):
    """SPEC-NTF-16 · TC-NTF-16c"""
    setup.ana.is_active = False

    setup.service.notify(setup.ana, setup.raul, setup.ticket, "m")

    assert setup.mail.sent == [(setup.ana, "m")]
    assert [n.status for n in setup.ticket.notifications] == ["sent"]
    assert setup.commit.calls == 1


def test_failed_send_is_recorded_with_the_error_and_does_not_raise():
    """SPEC-NTF-04 · TC-NTF-04a"""
    setup = Setup()
    service = NotificationService(
        {"mail": FailingStrategy("SMTP down")}, FakeClock(T0).now, setup.commit
    )

    service.notify(setup.ana, setup.raul, setup.ticket, "m")

    (notification,) = setup.ticket.notifications
    assert notification.status == "failed"
    assert notification.error == "SMTP down"
    assert notification.recipient is setup.ana
    assert notification.channel == "mail"
    assert notification.message == "m"
    assert notification.created_at == T0
    assert setup.commit.calls == 1


def test_notifying_the_actor_sends_and_records_nothing(setup):
    """SPEC-NTF-11 · TC-NTF-11a"""
    setup.service.notify(setup.ana, setup.ana, setup.ticket, "m")

    assert setup.mail.sent == []
    assert setup.ticket.notifications == []
    assert setup.commit.calls == 0


def test_notifying_the_actor_with_a_failing_strategy_leaves_no_trace():
    """SPEC-NTF-11 · TC-NTF-11b"""
    setup = Setup()
    service = NotificationService(
        {"mail": FailingStrategy("SMTP down")}, FakeClock(T0).now, setup.commit
    )

    service.notify(setup.raul, setup.raul, setup.ticket, "m")

    assert setup.ticket.notifications == []
    assert setup.commit.calls == 0
