from datetime import timedelta

import pytest

from app.domain.errors import PermissionDeniedError
from app.domain.products import Category, Product, ProductType
from app.domain.ticket import Ticket
from app.domain.users import Admin, Client, Representative
from app.services.ticket_service import TicketService
from tests.unit.catalog.fakes import FakeProductRepository
from tests.unit.fakes import CommitSpy, FakeClock
from tests.unit.tickets.fakes import FakeTicketNotifier, FakeTicketRepository
from tests.unit.users.fakes import FakeUserRepository


class Setup:
    def __init__(self) -> None:
        self.tickets = FakeTicketRepository()
        self.users = FakeUserRepository()
        self.products = FakeProductRepository()
        self.clock = FakeClock()
        self.commit = CommitSpy()
        self.notifier = FakeTicketNotifier()
        self.service = TicketService(
            self.tickets, self.users, self.products, self.clock.now, self.commit, self.notifier
        )
        self.ana = Client(name="Ana", email="ana@example.com", is_active=True)
        self.raul = Representative(name="Raul", email="raul@example.com", is_active=True)
        self.rosa = Representative(name="Rosa", email="rosa@example.com", is_active=True)
        self.root = Admin(name="Root", email="root@example.com", is_active=True)
        for user in (self.ana, self.raul, self.rosa, self.root):
            self.users.add(user)

    def add_product(self, name: str) -> Product:
        product_type = ProductType(name="Laptop", category=Category(name="Hardware"))
        product = Product(name=name, product_type=product_type, is_active=True)
        self.products.add(product)
        return product


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_create_ticket_saves_a_ticket_of_the_client_with_the_product(setup):
    """SPEC-TKT-01 · TC-TKT-01c"""
    xps = setup.add_product("XPS 13")

    ticket = setup.service.create_ticket(setup.ana.id, [xps.id], "Hola", setup.raul)

    assert isinstance(ticket, Ticket)
    assert ticket.client is setup.ana
    assert ticket.products == [xps]
    assert setup.tickets.tickets == [ticket]
    assert setup.commit.calls == 1


@pytest.mark.parametrize("product_ids", [None, []])
def test_create_ticket_without_products_creates_a_ticket_without_products(setup, product_ids):
    """SPEC-TKT-01 · TC-TKT-01d"""
    ticket = setup.service.create_ticket(setup.ana.id, product_ids, "Hola", setup.raul)

    assert ticket.products == []
    assert setup.tickets.tickets == [ticket]


def test_create_ticket_assigns_the_calling_representative(setup):
    """SPEC-TKT-02 · TC-TKT-02b"""
    ticket = setup.service.create_ticket(setup.ana.id, [], "Hola", setup.rosa)

    assert ticket.representative is setup.rosa


def test_create_ticket_records_the_initial_state_change_by_the_representative(setup):
    """SPEC-TKT-15 · TC-TKT-15c"""
    ticket = setup.service.create_ticket(setup.ana.id, [], "Hola", setup.raul)

    assert len(ticket.state_history) == 1
    change = ticket.state_history[0]
    assert change.state_name == "New"
    assert change.timestamp == setup.clock.now()
    assert change.user is setup.raul


def test_create_ticket_stamps_the_initial_records_with_the_injected_clock(setup):
    """SPEC-TKT-14 · TC-TKT-14f"""
    ticket = setup.service.create_ticket(setup.ana.id, [], "Hola", setup.raul)

    assert ticket.state_history[0].timestamp == setup.clock.now()
    assert ticket.milestones[0].created_at == setup.clock.now()


def test_create_ticket_takes_created_at_from_the_clock_on_every_call(setup):
    """SPEC-TKT-29 · TC-TKT-29e"""
    first_instant = setup.clock.now()
    first = setup.service.create_ticket(setup.ana.id, [], "Hola", setup.raul)
    setup.clock.advance(60)

    second = setup.service.create_ticket(setup.ana.id, [], "Hola otra vez", setup.raul)

    assert first.created_at == first_instant
    assert second.created_at == first_instant + timedelta(seconds=60)
    assert second.milestones[0].created_at == second.created_at
    assert second.state_history[0].timestamp == second.created_at


def test_create_ticket_associates_repeated_products_once(setup):
    """SPEC-TKT-31 · TC-TKT-31b"""
    xps = setup.add_product("XPS 13")
    desktop = setup.add_product("Desktop")

    ticket = setup.service.create_ticket(
        setup.ana.id, [xps.id, desktop.id, desktop.id], "Hola", setup.raul
    )

    assert sorted(p.name for p in ticket.products) == ["Desktop", "XPS 13"]
    assert len(ticket.products) == 2
    assert setup.commit.calls == 1


def test_create_ticket_rejects_a_client_actor(setup):
    """SPEC-TKT-05 · TC-TKT-05a"""
    with pytest.raises(PermissionDeniedError):
        setup.service.create_ticket(setup.ana.id, [], "Hola", setup.ana)

    assert setup.tickets.tickets == []
    assert setup.commit.calls == 0


def _create_ticket(setup: Setup, actor):
    return setup.service.create_ticket(setup.ana.id, [], "Hola", actor)


OPERATIONS = [pytest.param(_create_ticket, id="create_ticket")]


@pytest.mark.parametrize("operation", OPERATIONS)
def test_admin_is_denied_every_ticket_operation(setup, operation):
    """SPEC-TKT-27 · TC-TKT-27a"""
    with pytest.raises(PermissionDeniedError):
        operation(setup, setup.root)

    assert setup.tickets.tickets == []
    assert setup.commit.calls == 0
