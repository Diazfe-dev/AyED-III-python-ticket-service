"""Ticket use cases."""

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.domain.errors import (
    InvalidClientError,
    InvalidProductError,
    PermissionDeniedError,
    ProductNotInTicketError,
    TicketNotFoundError,
    ValidationError,
)
from app.domain.milestone import Milestone
from app.domain.paging import Page, PageRequest
from app.domain.products import Product
from app.domain.states import STATES
from app.domain.ticket import Ticket
from app.domain.users import Admin, Client, Representative, User
from app.services import notification_messages
from app.services.listing import page_request, search_text
from app.services.product_service import ProductRepository
from app.services.user_service import UserRepository
from app.services.validation import (
    INVALID,
    flag_error,
    id_error,
    id_list_error,
    parse_id,
    raise_if_invalid,
    text_error,
)


class TicketRepository(Protocol):
    def add(self, ticket: Ticket) -> None: ...

    def get_visible(self, ticket_id: int, actor: User) -> Ticket | None: ...

    def get_visible_with_milestones(self, ticket_id: int, actor: User) -> Ticket | None: ...

    def get(self, ticket_id: int) -> Ticket | None: ...

    def get_with_milestones(self, ticket_id: int) -> Ticket | None: ...

    def search(
        self,
        *,
        client_id: int | None = None,
        representative_id: int | None = None,
        state: str | None = None,
        q: str | None = None,
        ascending: bool = False,
        window: PageRequest | None = None,
    ) -> list[Ticket] | Page[Ticket]: ...


def _checked_listing(
    state: str | None,
    ids: dict[str, str | None],
    order: str | None,
    page: str | None,
    page_size: str | None,
) -> PageRequest | None:
    """The window asked for; raise one `ValidationError` with every malformed value."""
    errors = {
        "state": None if state is None or state in STATES else INVALID,
        **{name: None if value is None else id_error(value) for name, value in ids.items()},
        "order": None if order in (None, "asc", "desc") else INVALID,
    }
    try:
        window = page_request(page, page_size)
    except ValidationError as error:
        errors |= error.fields
        window = None
    raise_if_invalid(errors)
    return window


_LISTING_RULES: dict[str, tuple[tuple[str, ...], Callable[[User], dict[str, int]]]] = {
    "Admin": ((), lambda actor: {}),
    "Client": (("client_id", "representative_id"), lambda actor: {"client_id": actor.id}),
    "Representative": (("representative_id",), lambda actor: {"representative_id": actor.id}),
}


class TicketNotifier(Protocol):
    """Tells a participant about an event of the ticket."""

    def notify(self, recipient: User, actor: User, ticket: Ticket, message: str) -> None: ...


class TicketService:
    def __init__(
        self,
        tickets: TicketRepository,
        users: UserRepository,
        products: ProductRepository,
        clock: Callable[[], datetime],
        commit: Callable[[], None],
        notifier: TicketNotifier,
    ) -> None:
        self._tickets = tickets
        self._users = users
        self._products = products
        self._clock = clock
        self._commit = commit
        self._notifier = notifier

    def create_ticket(
        self,
        client_id: Any,
        product_ids: Any,
        first_message: Any,
        actor: User,
    ) -> Ticket:
        """Open a ticket for the client, assigned to the calling representative."""
        self._validate_creation(client_id, product_ids, first_message)
        if not isinstance(actor, Representative):
            raise PermissionDeniedError()
        client = self._find_client(parse_id(client_id))
        products = self._find_products(product_ids or [])
        ticket = Ticket.open(client, actor, products, first_message, self._clock())
        self._tickets.add(ticket)
        self._commit()
        self._notifier.notify(client, actor, ticket, notification_messages.ticket_created(ticket))
        return ticket

    def list_tickets(
        self,
        actor: User,
        state: str | None = None,
        client_id: str | None = None,
        representative_id: str | None = None,
        q: str | None = None,
        order: str | None = None,
        page: str | None = None,
        page_size: str | None = None,
    ) -> list[Ticket] | Page[Ticket]:
        """The tickets the actor may see, filtered; the query values come as text and are checked.

        Order of checks: format of every value (400), filters the role may not use (403), then the
        query, scoped by role (an admin sees all, a client its own, a representative its assigned).
        """
        filters = {"client_id": client_id, "representative_id": representative_id}
        window = _checked_listing(state, filters, order, page, page_size)
        forbidden, scope = _LISTING_RULES[actor.role]
        if any(filters[name] is not None for name in forbidden):
            raise PermissionDeniedError()
        chosen = {name: None if value is None else int(value) for name, value in filters.items()}
        return self._tickets.search(
            **chosen | scope(actor),
            state=state,
            q=search_text(q),
            ascending=order == "asc",
            window=window,
        )

    def get_ticket(self, ticket_id: int, actor: User) -> Ticket:
        """The ticket: any for the admin, else only if the actor is its client or representative."""
        lookup = {
            "Admin": lambda: self._tickets.get(ticket_id),
            "Client": lambda: self._tickets.get_visible(ticket_id, actor),
            "Representative": lambda: self._tickets.get_visible(ticket_id, actor),
        }[actor.role]
        ticket = lookup()
        if ticket is None:
            raise TicketNotFoundError()
        return ticket

    def close_ticket(self, ticket_id: int, actor: User) -> Ticket:
        """Close the ticket on behalf of its client or its assigned representative."""
        self._reject_admin(actor)
        ticket = self.get_ticket(ticket_id, actor)
        ticket.close(actor, self._clock())
        self._commit()
        self._notify_counterpart(ticket, actor, notification_messages.ticket_closed(ticket))
        return ticket

    def reopen_ticket(self, ticket_id: int, actor: User) -> Ticket:
        """Reopen a closed ticket; the representative that handled it stays assigned."""
        self._reject_admin(actor)
        ticket = self.get_ticket(ticket_id, actor)
        ticket.reopen(actor, self._clock())
        self._commit()
        self._notify_counterpart(ticket, actor, notification_messages.ticket_reopened(ticket))
        return ticket

    def add_products(self, ticket_id: int, product_ids: Any, actor: User) -> Ticket:
        """Associate active products with the ticket, all or nothing; only the assignee may."""
        raise_if_invalid({"product_ids": id_list_error(product_ids)})
        self._reject_admin(actor)
        ticket = self._assigned_ticket(ticket_id, actor)
        ticket.add_products(self._find_products(product_ids))
        self._commit()
        return ticket

    def add_milestone(
        self, ticket_id: int, content: Any, actor: User, start_progress: Any = False
    ) -> Milestone:
        """Record a milestone by the ticket's client or assigned representative."""
        raise_if_invalid(
            {"content": text_error(content), "start_progress": flag_error(start_progress)}
        )
        self._reject_admin(actor)
        ticket = self._visible_ticket(ticket_id, actor)
        now = self._clock()
        milestone = ticket.add_milestone(content, actor, now)
        by_representative = actor is ticket.representative
        changed = bool(start_progress and by_representative and ticket.request_progress(actor, now))
        self._commit()
        message = {
            True: notification_messages.milestone_and_state_changed,
            False: notification_messages.milestone_added,
        }[changed]
        self._notify_counterpart(ticket, actor, message(ticket))
        return milestone

    def list_milestones(self, ticket_id: int, actor: User) -> list[Milestone]:
        """The ticket's milestones in chronological order, whatever its state."""
        self._reject_admin(actor)
        ticket = self._tickets.get_visible_with_milestones(ticket_id, actor)
        if ticket is None:
            raise TicketNotFoundError()
        return list(ticket.milestones)

    def remove_product(self, ticket_id: int, product_id: int, actor: User) -> Ticket:
        """Remove a product from the ticket; only the assigned representative may."""
        self._reject_admin(actor)
        ticket = self._assigned_ticket(ticket_id, actor)
        ticket.remove_product(self._associated_product(ticket, product_id))
        self._commit()
        return ticket

    def _notify_counterpart(self, ticket: Ticket, actor: User, message: str) -> None:
        recipient = ticket.client if actor is ticket.representative else ticket.representative
        self._notifier.notify(recipient, actor, ticket, message)

    @staticmethod
    def _associated_product(ticket: Ticket, product_id: int) -> Product:
        product = next((p for p in ticket.products if p.id == product_id), None)
        if product is None:
            raise ProductNotInTicketError()
        return product

    def _assigned_ticket(self, ticket_id: int, actor: User) -> Ticket:
        ticket = self._visible_ticket(ticket_id, actor)
        if ticket.representative is not actor:
            raise PermissionDeniedError()
        return ticket

    @staticmethod
    def _reject_admin(actor: User) -> None:
        if isinstance(actor, Admin):
            raise PermissionDeniedError()

    def _visible_ticket(self, ticket_id: int, actor: User) -> Ticket:
        ticket = self._tickets.get_visible(ticket_id, actor)
        if ticket is None:
            raise TicketNotFoundError()
        return ticket

    def _validate_creation(self, client_id: Any, product_ids: Any, first_message: Any) -> None:
        raise_if_invalid(
            {
                "client_id": id_error(client_id),
                "product_ids": None
                if product_ids is None or product_ids == []
                else id_list_error(product_ids),
                "first_message": text_error(first_message),
            }
        )

    def _find_client(self, client_id: int) -> Client:
        client = self._users.get(client_id)
        if not isinstance(client, Client) or not client.is_active:
            raise InvalidClientError()
        return client

    def _find_products(self, product_ids: list[int]) -> list[Product]:
        wanted = list(dict.fromkeys(product_ids))
        products = self._products.get_many(wanted)
        if len(products) != len(wanted) or not all(p.is_active for p in products):
            raise InvalidProductError()
        return products
