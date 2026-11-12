import pytest

from app.domain.errors import (
    InvalidClientError,
    InvalidTransitionError,
    PermissionDeniedError,
    TicketClosedError,
    TicketNotFoundError,
    ValidationError,
)
from app.domain.products import Category, Product, ProductType
from app.domain.ticket import Ticket
from app.domain.users import Admin, Client, Representative
from app.services.ticket_service import TicketService
from tests.unit.catalog.fakes import FakeProductRepository
from tests.unit.fakes import CommitSpy, FakeClock
from tests.unit.tickets.fakes import FakeTicketNotifier, FakeTicketRepository
from tests.unit.users.fakes import FakeUserRepository


class CommitObservingNotifier(FakeTicketNotifier):
    """Records how many commits had happened when each notification was requested."""

    def __init__(self, commit: CommitSpy) -> None:
        super().__init__()
        self._commit = commit
        self.commits_seen: list[int] = []

    def notify(self, recipient, actor, ticket, message) -> None:
        self.commits_seen.append(self._commit.calls)
        super().notify(recipient, actor, ticket, message)


class Setup:
    def __init__(self) -> None:
        self.tickets = FakeTicketRepository()
        self.users = FakeUserRepository()
        self.clock = FakeClock()
        self.commit = CommitSpy()
        self.notifier = CommitObservingNotifier(self.commit)
        self.products = FakeProductRepository()
        self.service = TicketService(
            self.tickets,
            self.users,
            self.products,
            self.clock.now,
            self.commit,
            self.notifier,
        )
        self.ana = Client(name="Ana", email="ana@example.com", is_active=True)
        self.raul = Representative(name="Raul", email="raul@example.com", is_active=True)
        self.rosa = Representative(name="Rosa", email="rosa@example.com", is_active=True)
        self.root = Admin(name="Root", email="root@example.com", is_active=True)
        for user in (self.ana, self.raul, self.rosa, self.root):
            self.users.add(user)

    def add_ticket(self) -> Ticket:
        ticket = Ticket.open(self.ana, self.raul, [], "Hola", self.clock.now())
        self.tickets.add(ticket)
        return ticket

    def add_product(self) -> Product:
        product_type = ProductType(name="Laptop", category=Category(name="Hardware"))
        product = Product(name="XPS 13", product_type=product_type, is_active=True)
        self.products.add(product)
        return product


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_create_ticket_notifies_the_client_once(setup):
    """SPEC-NTF-05 · TC-NTF-05a"""
    ticket = setup.service.create_ticket(setup.ana.id, [], "Hola", setup.raul)

    (recipient, actor, notified, message) = setup.notifier.calls[0]
    assert len(setup.notifier.calls) == 1
    assert (recipient, actor, notified) == (setup.ana, setup.raul, ticket)
    assert f"#{ticket.id}" in message
    assert "created" in message


def test_create_ticket_notifies_after_the_commit(setup):
    """SPEC-NTF-15 · TC-NTF-15c"""
    setup.service.create_ticket(setup.ana.id, [], "Hola", setup.raul)

    assert setup.notifier.commits_seen == [1]


def test_representative_close_notifies_the_client(setup):
    """SPEC-NTF-07 · TC-NTF-07a"""
    ticket = setup.add_ticket()

    setup.service.close_ticket(ticket.id, setup.raul)

    ((recipient, actor, notified, message),) = setup.notifier.calls
    assert (recipient, actor, notified) == (setup.ana, setup.raul, ticket)
    assert f"#{ticket.id}" in message
    assert "closed" in message
    assert "Closed" in message


def test_representative_reopen_notifies_the_client(setup):
    """SPEC-NTF-07 · TC-NTF-07b"""
    ticket = setup.add_ticket()
    ticket.close(setup.raul, setup.clock.now())

    setup.service.reopen_ticket(ticket.id, setup.raul)

    ((recipient, actor, notified, message),) = setup.notifier.calls
    assert (recipient, actor, notified) == (setup.ana, setup.raul, ticket)
    assert "reopened" in message
    assert "InProgress" in message


def test_client_reopen_notifies_the_representative(setup):
    """SPEC-NTF-10 · TC-NTF-10a"""
    ticket = setup.add_ticket()
    ticket.close(setup.raul, setup.clock.now())

    setup.service.reopen_ticket(ticket.id, setup.ana)

    ((recipient, actor, notified, message),) = setup.notifier.calls
    assert (recipient, actor, notified) == (setup.raul, setup.ana, ticket)
    assert "reopened" in message


def test_client_close_notifies_the_representative(setup):
    """SPEC-NTF-13 · TC-NTF-13a"""
    ticket = setup.add_ticket()

    setup.service.close_ticket(ticket.id, setup.ana)

    ((recipient, actor, notified, message),) = setup.notifier.calls
    assert (recipient, actor, notified) == (setup.raul, setup.ana, ticket)
    assert "closed" in message


def test_close_and_reopen_notify_after_the_commit(setup):
    """SPEC-NTF-15 · TC-NTF-15c"""
    ticket = setup.add_ticket()

    setup.service.close_ticket(ticket.id, setup.raul)
    setup.service.reopen_ticket(ticket.id, setup.raul)

    assert setup.notifier.commits_seen == [1, 2]


def test_representative_milestone_notifies_the_client(setup):
    """SPEC-NTF-06 · TC-NTF-06a"""
    ticket = setup.add_ticket()

    setup.service.add_milestone(ticket.id, "Revisando", setup.raul)

    ((recipient, actor, notified, message),) = setup.notifier.calls
    assert (recipient, actor, notified) == (setup.ana, setup.raul, ticket)
    assert "milestone" in message
    assert "InProgress" not in message


def test_redundant_start_progress_sends_the_plain_milestone_message(setup):
    """SPEC-NTF-06 · TC-NTF-06b (dec. 5)"""
    ticket = setup.add_ticket()
    ticket.start_progress(setup.raul, setup.clock.now())

    setup.service.add_milestone(ticket.id, "Sigo", setup.raul, start_progress=True)

    ((_, _, _, message),) = setup.notifier.calls
    assert "milestone" in message
    assert "InProgress" not in message


def test_milestone_that_starts_progress_sends_one_combined_notification(setup):
    """SPEC-NTF-08 · TC-NTF-08b (dec. 5)"""
    ticket = setup.add_ticket()

    setup.service.add_milestone(ticket.id, "Empiezo", setup.raul, start_progress=True)

    ((recipient, actor, notified, message),) = setup.notifier.calls
    assert (recipient, actor, notified) == (setup.ana, setup.raul, ticket)
    assert "milestone" in message
    assert "InProgress" in message


@pytest.mark.parametrize("start_progress", [False, True])
def test_client_milestone_notifies_the_representative(setup, start_progress):
    """SPEC-NTF-09 · TC-NTF-09a"""
    ticket = setup.add_ticket()

    setup.service.add_milestone(ticket.id, "Gracias", setup.ana, start_progress=start_progress)

    ((recipient, actor, notified, message),) = setup.notifier.calls
    assert (recipient, actor, notified) == (setup.raul, setup.ana, ticket)
    assert "milestone" in message
    assert "InProgress" not in message


def test_milestone_notifies_after_the_commit(setup):
    """SPEC-NTF-15 · TC-NTF-15c"""
    ticket = setup.add_ticket()

    setup.service.add_milestone(ticket.id, "Revisando", setup.raul)

    assert setup.notifier.commits_seen == [1]


class FailingCommit:
    def __call__(self) -> None:
        raise RuntimeError("commit failed")


def _closed_ticket(setup: Setup) -> Ticket:
    ticket = setup.add_ticket()
    ticket.close(setup.raul, setup.clock.now())
    return ticket


REJECTED_OPERATIONS = {
    "create_invalid_body": (
        ValidationError,
        lambda s: s.service.create_ticket("x", [], "Hola", s.raul),
    ),
    "create_by_client": (
        PermissionDeniedError,
        lambda s: s.service.create_ticket(s.ana.id, [], "Hola", s.ana),
    ),
    "create_unknown_client": (
        InvalidClientError,
        lambda s: s.service.create_ticket(999, [], "Hola", s.raul),
    ),
    "close_foreign": (
        TicketNotFoundError,
        lambda s: s.service.close_ticket(s.add_ticket().id, s.rosa),
    ),
    "close_by_admin": (
        PermissionDeniedError,
        lambda s: s.service.close_ticket(s.add_ticket().id, s.root),
    ),
    "close_closed": (
        InvalidTransitionError,
        lambda s: s.service.close_ticket(_closed_ticket(s).id, s.raul),
    ),
    "reopen_open": (
        InvalidTransitionError,
        lambda s: s.service.reopen_ticket(s.add_ticket().id, s.raul),
    ),
    "milestone_empty": (
        ValidationError,
        lambda s: s.service.add_milestone(s.add_ticket().id, "", s.raul),
    ),
    "milestone_closed": (
        TicketClosedError,
        lambda s: s.service.add_milestone(_closed_ticket(s).id, "Hola", s.raul),
    ),
    "milestone_foreign": (
        TicketNotFoundError,
        lambda s: s.service.add_milestone(s.add_ticket().id, "Hola", s.rosa),
    ),
}


@pytest.mark.parametrize("name", list(REJECTED_OPERATIONS))
def test_rejected_operation_does_not_notify(setup, name):
    """SPEC-NTF-15 · TC-NTF-15a"""
    error, operation = REJECTED_OPERATIONS[name]

    with pytest.raises(error):
        operation(setup)

    assert setup.notifier.calls == []
    assert setup.commit.calls == 0


NOTIFYING_OPERATIONS = {
    "create": lambda s: s.service.create_ticket(s.ana.id, [], "Hola", s.raul),
    "close": lambda s: s.service.close_ticket(s.add_ticket().id, s.raul),
    "reopen": lambda s: s.service.reopen_ticket(_closed_ticket(s).id, s.raul),
    "milestone": lambda s: s.service.add_milestone(s.add_ticket().id, "Hola", s.raul),
}


@pytest.mark.parametrize("name", list(NOTIFYING_OPERATIONS))
def test_failing_commit_does_not_notify(setup, name):
    """SPEC-NTF-15 · TC-NTF-15d"""
    operation = NOTIFYING_OPERATIONS[name]
    setup.service = TicketService(
        setup.tickets,
        setup.users,
        setup.products,
        setup.clock.now,
        FailingCommit(),
        setup.notifier,
    )

    with pytest.raises(RuntimeError):
        operation(setup)

    assert setup.notifier.calls == []


def test_adding_and_removing_products_does_not_notify(setup):
    """SPEC-NTF-17 · TC-NTF-17a (dec. 12)"""
    ticket = setup.add_ticket()
    product = setup.add_product()

    setup.service.add_products(ticket.id, [product.id], setup.raul)
    setup.service.remove_product(ticket.id, product.id, setup.raul)

    assert setup.notifier.calls == []
    assert setup.commit.calls == 2
