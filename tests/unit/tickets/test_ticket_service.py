from datetime import UTC, timedelta

import pytest

from app.domain.errors import (
    InvalidClientError,
    InvalidProductError,
    InvalidTransitionError,
    PermissionDeniedError,
    ProductNotInTicketError,
    TicketNotFoundError,
    ValidationError,
)
from app.domain.products import Category, Product, ProductType
from app.domain.ticket import Ticket
from app.domain.users import Admin, Client, Representative
from app.services.ticket_service import TicketService
from app.wiring import utc_now
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

    def add_ticket(self, client, representative, products=()) -> Ticket:
        ticket = Ticket.open(client, representative, products, "Hola", self.clock.now())
        self.tickets.add(ticket)
        return ticket

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
    created_at = setup.clock.now()
    ticket = setup.service.create_ticket(setup.ana.id, [], "Hola", setup.raul)
    setup.clock.advance(60)

    setup.service.close_ticket(ticket.id, setup.ana)

    assert ticket.state_history[0].timestamp == created_at
    assert ticket.milestones[0].created_at == created_at
    assert ticket.state_history[1].timestamp == created_at + timedelta(seconds=60)


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


@pytest.mark.parametrize("first_message", [None, "", "   "])
def test_create_ticket_rejects_a_missing_or_blank_first_message(setup, first_message):
    """SPEC-TKT-23 · TC-TKT-23a"""
    with pytest.raises(ValidationError) as error:
        setup.service.create_ticket(setup.ana.id, [], first_message, setup.raul)

    assert error.value.fields == {"first_message": "required"}
    assert setup.tickets.tickets == []
    assert setup.commit.calls == 0


@pytest.mark.parametrize("first_message", [123, ["Hola"], {"a": 1}])
def test_create_ticket_rejects_a_first_message_that_is_not_text(setup, first_message):
    """SPEC-TKT-23 · TC-TKT-23b"""
    with pytest.raises(ValidationError) as error:
        setup.service.create_ticket(setup.ana.id, [], first_message, setup.raul)

    assert error.value.fields == {"first_message": "invalid"}
    assert setup.commit.calls == 0


@pytest.mark.parametrize(
    ("client_id", "reason"),
    [
        (True, "invalid"),
        (0, "invalid"),
        (-1, "invalid"),
        (1.5, "invalid"),
        ("abc", "invalid"),
        ("", "invalid"),
        ([1], "invalid"),
        (None, "required"),
    ],
)
def test_create_ticket_rejects_a_malformed_client_id(setup, client_id, reason):
    """SPEC-TKT-24 · TC-TKT-24a"""
    with pytest.raises(ValidationError) as error:
        setup.service.create_ticket(client_id, [], "Hola", setup.raul)

    assert error.value.fields == {"client_id": reason}
    assert setup.tickets.tickets == []
    assert setup.commit.calls == 0


@pytest.mark.parametrize(
    "product_ids", ["abc", "", 0, 5, {"a": 1}, [0], [True], [1, "x"], [1.5], ["1"]]
)
def test_create_ticket_rejects_malformed_product_ids(setup, product_ids):
    """SPEC-TKT-24 · TC-TKT-24b"""
    with pytest.raises(ValidationError) as error:
        setup.service.create_ticket(setup.ana.id, product_ids, "Hola", setup.raul)

    assert error.value.fields == {"product_ids": "invalid"}
    assert setup.commit.calls == 0


def test_create_ticket_reports_every_invalid_field_together(setup):
    """SPEC-TKT-24 · TC-TKT-24c"""
    with pytest.raises(ValidationError) as error:
        setup.service.create_ticket("x", "y", "", setup.raul)

    assert error.value.fields == {
        "client_id": "invalid",
        "product_ids": "invalid",
        "first_message": "required",
    }
    assert setup.commit.calls == 0


def test_create_ticket_accepts_a_client_id_written_as_digits(setup):
    """SPEC-TKT-24 · TC-TKT-24d"""
    xps = setup.add_product("XPS 13")

    ticket = setup.service.create_ticket(str(setup.ana.id), [xps.id], "Hola", setup.raul)

    assert ticket.client is setup.ana
    assert ticket.products == [xps]


def test_create_ticket_rejects_an_unknown_client(setup):
    """SPEC-TKT-06 · TC-TKT-06a"""
    with pytest.raises(InvalidClientError):
        setup.service.create_ticket(9999, [], "Hola", setup.raul)

    assert setup.tickets.tickets == []
    assert setup.commit.calls == 0


@pytest.mark.parametrize("role_user", ["rosa", "root"])
def test_create_ticket_rejects_a_client_id_of_another_role(setup, role_user):
    """SPEC-TKT-06 · TC-TKT-06b"""
    other = getattr(setup, role_user)

    with pytest.raises(InvalidClientError):
        setup.service.create_ticket(other.id, [], "Hola", setup.raul)

    assert setup.commit.calls == 0


def test_create_ticket_rejects_an_inactive_client(setup):
    """SPEC-TKT-06 · TC-TKT-06c"""
    setup.ana.is_active = False

    with pytest.raises(InvalidClientError):
        setup.service.create_ticket(setup.ana.id, [], "Hola", setup.raul)

    assert setup.commit.calls == 0


def test_create_ticket_rejects_an_unknown_product(setup):
    """SPEC-TKT-08 · TC-TKT-08d"""
    xps = setup.add_product("XPS 13")

    with pytest.raises(InvalidProductError):
        setup.service.create_ticket(setup.ana.id, [xps.id, 9999], "Hola", setup.raul)

    assert setup.tickets.tickets == []
    assert setup.commit.calls == 0


def test_create_ticket_rejects_an_inactive_product(setup):
    """SPEC-TKT-08 · TC-TKT-08e"""
    optiplex = setup.add_product("Optiplex")
    optiplex.is_active = False

    with pytest.raises(InvalidProductError):
        setup.service.create_ticket(setup.ana.id, [optiplex.id], "Hola", setup.raul)

    assert setup.commit.calls == 0


def test_create_ticket_with_one_invalid_product_creates_nothing(setup):
    """SPEC-TKT-08 · TC-TKT-08f"""
    xps = setup.add_product("XPS 13")
    optiplex = setup.add_product("Optiplex")
    optiplex.is_active = False

    with pytest.raises(InvalidProductError):
        setup.service.create_ticket(setup.ana.id, [xps.id, optiplex.id], "Hola", setup.raul)

    assert setup.tickets.tickets == []
    assert setup.commit.calls == 0


def _create_ticket(setup: Setup, ticket_id, actor):
    return setup.service.create_ticket(setup.ana.id, [], "Hola", actor)


def _get_ticket(setup: Setup, ticket_id, actor):
    return setup.service.get_ticket(ticket_id, actor)


def _close_ticket(setup: Setup, ticket_id, actor):
    return setup.service.close_ticket(ticket_id, actor)


def _reopen_ticket(setup: Setup, ticket_id, actor):
    return setup.service.reopen_ticket(ticket_id, actor)


def _add_products(setup: Setup, ticket_id, actor):
    return setup.service.add_products(ticket_id, [1], actor)


def _remove_product(setup: Setup, ticket_id, actor):
    return setup.service.remove_product(ticket_id, 1, actor)


def _list_tickets(setup: Setup, ticket_id, actor):
    return setup.service.list_tickets(actor)


TICKET_OPERATIONS = [
    pytest.param(_get_ticket, id="get_ticket"),
    pytest.param(_close_ticket, id="close_ticket"),
    pytest.param(_reopen_ticket, id="reopen_ticket"),
    pytest.param(_add_products, id="add_products"),
    pytest.param(_remove_product, id="remove_product"),
]
OPERATIONS = [
    pytest.param(_create_ticket, id="create_ticket"),
    pytest.param(_list_tickets, id="list_tickets"),
    *TICKET_OPERATIONS,
]


def _assert_untouched(setup: Setup, tickets: list[Ticket]) -> None:
    assert setup.tickets.tickets == tickets
    assert setup.commit.calls == 0


@pytest.mark.parametrize("operation", OPERATIONS)
def test_admin_is_denied_every_ticket_operation(setup, operation):
    """SPEC-TKT-27 · TC-TKT-27a"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(PermissionDeniedError):
        operation(setup, ticket.id, setup.root)

    _assert_untouched(setup, [ticket])


def test_get_ticket_returns_the_ticket_to_the_owner_client(setup):
    """SPEC-TKT-28 · TC-TKT-28a"""
    xps = setup.add_product("XPS 13")
    ticket = setup.add_ticket(setup.ana, setup.raul, [xps])

    found = setup.service.get_ticket(ticket.id, setup.ana)

    assert found is ticket
    assert found.state.name == "New"
    assert found.client is setup.ana
    assert found.representative is setup.raul
    assert found.products == [xps]


def test_get_ticket_returns_the_ticket_to_the_assigned_representative(setup):
    """SPEC-TKT-28 · TC-TKT-28b"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    assert setup.service.get_ticket(ticket.id, setup.raul) is ticket


@pytest.mark.parametrize("operation", TICKET_OPERATIONS)
def test_another_client_gets_not_found_on_every_ticket_operation(setup, operation):
    """SPEC-TKT-19 · TC-TKT-19a"""
    beto = Client(name="Beto", email="beto@example.com", is_active=True)
    setup.users.add(beto)
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(TicketNotFoundError):
        operation(setup, ticket.id, beto)

    _assert_untouched(setup, [ticket])


@pytest.mark.parametrize("operation", TICKET_OPERATIONS)
def test_unassigned_representative_gets_not_found_on_every_ticket_operation(setup, operation):
    """SPEC-TKT-20 · TC-TKT-20a"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(TicketNotFoundError):
        operation(setup, ticket.id, setup.rosa)

    _assert_untouched(setup, [ticket])


@pytest.mark.parametrize("operation", TICKET_OPERATIONS)
def test_a_missing_ticket_gets_not_found_on_every_ticket_operation(setup, operation):
    """SPEC-TKT-30 · TC-TKT-30a"""
    with pytest.raises(TicketNotFoundError):
        operation(setup, 9999, setup.ana)

    _assert_untouched(setup, [])


def test_list_tickets_returns_only_the_tickets_of_the_client(setup):
    """SPEC-TKT-17 · TC-TKT-17a"""
    beto = Client(name="Beto", email="beto@example.com", is_active=True)
    setup.users.add(beto)
    mine = setup.add_ticket(setup.ana, setup.raul)
    setup.add_ticket(beto, setup.raul)

    assert setup.service.list_tickets(setup.ana) == [mine]


def test_list_tickets_returns_only_the_tickets_assigned_to_the_representative(setup):
    """SPEC-TKT-18 · TC-TKT-18a"""
    mine = setup.add_ticket(setup.ana, setup.raul)
    setup.add_ticket(setup.ana, setup.rosa)

    assert setup.service.list_tickets(setup.raul) == [mine]


def test_list_tickets_puts_the_most_recent_first_for_both_roles(setup):
    """SPEC-TKT-29 · TC-TKT-29a"""
    first = setup.service.create_ticket(setup.ana.id, [], "Uno", setup.raul)
    setup.clock.advance(60)
    second = setup.service.create_ticket(setup.ana.id, [], "Dos", setup.raul)
    setup.clock.advance(60)
    third = setup.service.create_ticket(setup.ana.id, [], "Tres", setup.raul)

    assert setup.service.list_tickets(setup.raul) == [third, second, first]
    assert setup.service.list_tickets(setup.ana) == [third, second, first]


def test_list_tickets_breaks_ties_by_descending_id(setup):
    """SPEC-TKT-29 · TC-TKT-29d"""
    older = setup.add_ticket(setup.ana, setup.raul)
    setup.clock.advance(60)
    same_a = setup.add_ticket(setup.ana, setup.raul)
    same_b = setup.add_ticket(setup.ana, setup.raul)

    assert setup.service.list_tickets(setup.raul) == [same_b, same_a, older]


def test_owner_client_closes_the_ticket(setup):
    """SPEC-TKT-10 · TC-TKT-10c"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    closed = setup.service.close_ticket(ticket.id, setup.ana)

    assert closed is ticket
    assert closed.state.name == "Closed"
    assert setup.commit.calls == 1


def test_assigned_representative_closes_the_ticket(setup):
    """SPEC-TKT-10 · TC-TKT-10d"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    closed = setup.service.close_ticket(ticket.id, setup.raul)

    assert closed.state.name == "Closed"
    assert closed.state_history[-1].user is setup.raul
    assert setup.commit.calls == 1


def _closed_ticket(setup: Setup) -> Ticket:
    ticket = setup.add_ticket(setup.ana, setup.raul)
    ticket.close(setup.raul, setup.clock.now())
    return ticket


def test_owner_client_reopens_a_closed_ticket(setup):
    """SPEC-TKT-11 · TC-TKT-11b"""
    ticket = _closed_ticket(setup)

    reopened = setup.service.reopen_ticket(ticket.id, setup.ana)

    assert reopened.state.name == "InProgress"
    assert setup.commit.calls == 1


def test_assigned_representative_reopens_a_closed_ticket(setup):
    """SPEC-TKT-11 · TC-TKT-11c"""
    ticket = _closed_ticket(setup)

    reopened = setup.service.reopen_ticket(ticket.id, setup.raul)

    assert reopened.state.name == "InProgress"
    assert setup.commit.calls == 1


def test_reopening_keeps_the_representative_even_if_they_are_inactive(setup):
    """SPEC-TKT-12 · TC-TKT-12b"""
    ticket = _closed_ticket(setup)
    setup.raul.deactivate()

    reopened = setup.service.reopen_ticket(ticket.id, setup.ana)

    assert reopened.state.name == "InProgress"
    assert reopened.representative is setup.raul


def test_invalid_transitions_raise_without_commit_or_changes(setup):
    """SPEC-TKT-13 · TC-TKT-13d"""
    closed = _closed_ticket(setup)
    new = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(InvalidTransitionError):
        setup.service.close_ticket(closed.id, setup.ana)
    with pytest.raises(InvalidTransitionError):
        setup.service.reopen_ticket(new.id, setup.ana)

    assert setup.commit.calls == 0
    assert closed.state.name == "Closed"
    assert len(closed.state_history) == 2
    assert new.state.name == "New"
    assert len(new.state_history) == 1


def test_assigned_representative_adds_a_product_to_the_ticket(setup):
    """SPEC-TKT-07 · TC-TKT-07c"""
    xps = setup.add_product("XPS 13")
    ticket = setup.add_ticket(setup.ana, setup.raul)

    result = setup.service.add_products(ticket.id, [xps.id], setup.raul)

    assert result is ticket
    assert ticket.products == [xps]
    assert setup.commit.calls == 1


def test_products_can_be_added_to_a_closed_ticket(setup):
    """SPEC-TKT-07 · TC-TKT-07e"""
    xps = setup.add_product("XPS 13")
    ticket = _closed_ticket(setup)

    result = setup.service.add_products(ticket.id, [xps.id], setup.raul)

    assert result.products == [xps]
    assert result.state.name == "Closed"
    assert setup.commit.calls == 1


def test_adding_an_unknown_product_changes_nothing(setup):
    """SPEC-TKT-08 · TC-TKT-08g"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(InvalidProductError):
        setup.service.add_products(ticket.id, [9999], setup.raul)

    assert ticket.products == []
    assert setup.commit.calls == 0


def test_adding_an_inactive_product_changes_nothing(setup):
    """SPEC-TKT-08 · TC-TKT-08h"""
    optiplex = setup.add_product("Optiplex")
    optiplex.is_active = False
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(InvalidProductError):
        setup.service.add_products(ticket.id, [optiplex.id], setup.raul)

    assert ticket.products == []
    assert setup.commit.calls == 0


def test_adding_a_valid_and_an_inactive_product_associates_none(setup):
    """SPEC-TKT-08 · TC-TKT-08i"""
    xps = setup.add_product("XPS 13")
    optiplex = setup.add_product("Optiplex")
    optiplex.is_active = False
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(InvalidProductError):
        setup.service.add_products(ticket.id, [xps.id, optiplex.id], setup.raul)

    assert ticket.products == []
    assert setup.commit.calls == 0


def test_adding_a_valid_and_an_unknown_product_associates_none(setup):
    """SPEC-TKT-08 · TC-TKT-08l"""
    xps = setup.add_product("XPS 13")
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(InvalidProductError):
        setup.service.add_products(ticket.id, [xps.id, 9999], setup.raul)

    assert ticket.products == []
    assert setup.commit.calls == 0


def test_the_owner_client_cannot_add_products(setup):
    """SPEC-TKT-22 · TC-TKT-22a"""
    xps = setup.add_product("XPS 13")
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(PermissionDeniedError):
        setup.service.add_products(ticket.id, [xps.id], setup.ana)

    assert ticket.products == []
    assert setup.commit.calls == 0


def test_the_owner_client_gets_validation_before_forbidden_on_add_products(setup):
    """SPEC-TKT-22 · TC-TKT-22e"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(ValidationError) as error:
        setup.service.add_products(ticket.id, "abc", setup.ana)
    with pytest.raises(PermissionDeniedError):
        setup.service.add_products(ticket.id, [9999], setup.ana)

    assert error.value.fields == {"product_ids": "invalid"}
    assert ticket.products == []
    assert setup.commit.calls == 0


@pytest.mark.parametrize(
    ("product_ids", "reason"),
    [
        (None, "required"),
        ([], "invalid"),
        ("abc", "invalid"),
        (5, "invalid"),
        ([0], "invalid"),
        ([True], "invalid"),
        (["1"], "invalid"),
        ([1, "x"], "invalid"),
    ],
)
def test_add_products_rejects_a_malformed_product_ids_body(setup, product_ids, reason):
    """SPEC-TKT-24 · TC-TKT-24g"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(ValidationError) as error:
        setup.service.add_products(ticket.id, product_ids, setup.raul)

    assert error.value.fields == {"product_ids": reason}
    assert ticket.products == []
    assert setup.commit.calls == 0


def test_add_products_validates_the_body_before_looking_up_the_ticket(setup):
    """SPEC-TKT-24 · TC-TKT-24j"""
    mine = setup.add_ticket(setup.ana, setup.raul)
    theirs = setup.add_ticket(setup.ana, setup.rosa)

    for ticket_id in (mine.id, theirs.id, 9999):
        with pytest.raises(ValidationError) as error:
            setup.service.add_products(ticket_id, "abc", setup.raul)
        assert error.value.fields == {"product_ids": "invalid"}

    assert setup.tickets.visible_lookups == []
    assert setup.commit.calls == 0


def test_add_products_associates_each_product_once(setup):
    """SPEC-TKT-25 · TC-TKT-25b"""
    xps = setup.add_product("XPS 13")
    desktop = setup.add_product("Desktop")
    ticket = setup.add_ticket(setup.ana, setup.raul, [xps])

    setup.service.add_products(ticket.id, [xps.id, desktop.id], setup.raul)
    setup.service.add_products(ticket.id, [desktop.id, desktop.id], setup.raul)

    assert sorted(p.name for p in ticket.products) == ["Desktop", "XPS 13"]
    assert setup.commit.calls == 2


def test_assigned_representative_removes_a_product(setup):
    """SPEC-TKT-21 · TC-TKT-21c"""
    xps = setup.add_product("XPS 13")
    ticket = setup.add_ticket(setup.ana, setup.raul, [xps])

    setup.service.remove_product(ticket.id, xps.id, setup.raul)

    assert ticket.products == []
    assert setup.commit.calls == 1


def test_a_product_can_be_removed_from_a_closed_ticket(setup):
    """SPEC-TKT-21 · TC-TKT-21e"""
    xps = setup.add_product("XPS 13")
    ticket = _closed_ticket(setup)
    ticket.add_products([xps])

    setup.service.remove_product(ticket.id, xps.id, setup.raul)

    assert ticket.products == []
    assert ticket.state.name == "Closed"
    assert setup.commit.calls == 1


def test_the_owner_client_cannot_remove_products(setup):
    """SPEC-TKT-22 · TC-TKT-22b"""
    xps = setup.add_product("XPS 13")
    ticket = setup.add_ticket(setup.ana, setup.raul, [xps])

    with pytest.raises(PermissionDeniedError):
        setup.service.remove_product(ticket.id, xps.id, setup.ana)

    assert ticket.products == [xps]
    assert setup.commit.calls == 0


def test_forbidden_wins_over_product_not_in_ticket_on_remove_product(setup):
    """SPEC-TKT-22 · TC-TKT-22e"""
    ticket = setup.add_ticket(setup.ana, setup.raul)

    with pytest.raises(PermissionDeniedError):
        setup.service.remove_product(ticket.id, 9999, setup.ana)

    assert setup.commit.calls == 0


def test_removing_a_product_that_is_not_in_the_ticket_fails(setup):
    """SPEC-TKT-26 · TC-TKT-26b"""
    xps = setup.add_product("XPS 13")
    desktop = setup.add_product("Desktop")
    ticket = setup.add_ticket(setup.ana, setup.raul, [xps])

    with pytest.raises(ProductNotInTicketError):
        setup.service.remove_product(ticket.id, desktop.id, setup.raul)

    assert ticket.products == [xps]
    assert setup.commit.calls == 0


def test_utc_now_returns_a_timezone_aware_utc_datetime():
    """SPEC-TKT-14 · TC-TKT-14h"""
    now = utc_now()

    assert now.tzinfo is UTC
