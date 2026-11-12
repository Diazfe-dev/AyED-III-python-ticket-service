from datetime import UTC, datetime

from app.domain.ticket import Ticket
from app.domain.users import Client, Representative
from app.services.notification_service import NotificationService
from app.services.ticket_service import TicketService
from tests.unit.catalog.fakes import FakeProductRepository
from tests.unit.fakes import CommitSpy, FakeClock
from tests.unit.notifications.fakes import FailingStrategy, RecordingStrategy
from tests.unit.tickets.fakes import FakeTicketRepository
from tests.unit.users.fakes import FakeUserRepository

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class Setup:
    """A `TicketService` wired to a real `NotificationService` with the given strategy."""

    def __init__(self, strategy: RecordingStrategy | FailingStrategy) -> None:
        self.ana = Client(name="Ana", email="ana@example.com", preferred_channel="mail")
        self.raul = Representative(name="Raul", email="raul@example.com", preferred_channel="mail")
        self.commit = CommitSpy()
        clock = FakeClock(T0)
        self.tickets = FakeTicketRepository()
        users = FakeUserRepository()
        for user in (self.ana, self.raul):
            users.add(user)
        notifier = NotificationService({"mail": strategy}, clock.now, self.commit)
        self.service = TicketService(
            self.tickets, users, FakeProductRepository(), clock.now, self.commit, notifier
        )
        self.ticket = Ticket.open(self.ana, self.raul, [], "Hola", T0)
        self.tickets.add(self.ticket)


def test_a_failed_send_does_not_undo_the_operation():
    """SPEC-NTF-14 · TC-NTF-14a"""
    setup = Setup(FailingStrategy("SMTP down"))

    ticket = setup.service.close_ticket(setup.ticket.id, setup.raul)

    assert setup.commit.calls == 2
    assert ticket.state_name == "Closed"
    assert ticket.state_history[-1].state_name == "Closed"
    (notification,) = ticket.notifications
    assert notification.status == "failed"


def test_a_failed_send_returns_the_same_result_as_a_successful_one():
    """SPEC-NTF-19 · TC-NTF-19b"""
    sent = Setup(RecordingStrategy())
    failed = Setup(FailingStrategy("SMTP down"))

    sent_ticket = sent.service.close_ticket(sent.ticket.id, sent.raul)
    failed_ticket = failed.service.close_ticket(failed.ticket.id, failed.raul)

    assert sent_ticket.state_name == failed_ticket.state_name == "Closed"
    assert [(c.state_name, c.timestamp) for c in sent_ticket.state_history] == [
        (c.state_name, c.timestamp) for c in failed_ticket.state_history
    ]
