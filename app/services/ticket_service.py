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
)
from app.domain.products import Product
from app.domain.ticket import Ticket
from app.domain.users import Admin, Client, Representative, User
from app.services.product_service import ProductRepository
from app.services.user_service import UserRepository
from app.services.validation import id_error, id_list_error, parse_id, raise_if_invalid, text_error


class TicketRepository(Protocol):
    def add(self, ticket: Ticket) -> None: ...

    def get_visible(self, ticket_id: int, actor: User) -> Ticket | None: ...

    def list_by_client(self, client_id: int) -> list[Ticket]: ...

    def list_by_representative(self, representative_id: int) -> list[Ticket]: ...


class TicketNotifier(Protocol):
    """Extension point for the notifications area."""

    def notify(self, recipient: User, actor: User, ticket: Ticket, message: str) -> None: ...


class NullTicketNotifier:
    """Notifier that does nothing, until the notifications area provides the real one."""

    def notify(self, recipient: User, actor: User, ticket: Ticket, message: str) -> None:
        return None


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
        if not isinstance(actor, Representative):
            raise PermissionDeniedError()
        self._validate_creation(client_id, product_ids, first_message)
        client = self._find_client(parse_id(client_id))
        products = self._find_products(product_ids or [])
        ticket = Ticket.open(client, actor, products, first_message, self._clock())
        self._tickets.add(ticket)
        self._commit()
        return ticket

    def list_tickets(self, actor: User) -> list[Ticket]:
        """The actor's tickets, newest first: the client's own or the ones assigned to them."""
        self._reject_admin(actor)
        listing = {
            "Client": self._tickets.list_by_client,
            "Representative": self._tickets.list_by_representative,
        }[actor.role]
        return listing(actor.id)

    def get_ticket(self, ticket_id: int, actor: User) -> Ticket:
        """The ticket, if the actor is its client or its assigned representative."""
        self._reject_admin(actor)
        return self._visible_ticket(ticket_id, actor)

    def close_ticket(self, ticket_id: int, actor: User) -> Ticket:
        """Close the ticket on behalf of its client or its assigned representative."""
        ticket = self.get_ticket(ticket_id, actor)
        ticket.close(actor, self._clock())
        self._commit()
        return ticket

    def reopen_ticket(self, ticket_id: int, actor: User) -> Ticket:
        """Reopen a closed ticket; the representative that handled it stays assigned."""
        ticket = self.get_ticket(ticket_id, actor)
        ticket.reopen(actor, self._clock())
        self._commit()
        return ticket

    def add_products(self, ticket_id: int, product_ids: Any, actor: User) -> Ticket:
        """Associate active products with the ticket, all or nothing; only the assignee may."""
        self._reject_admin(actor)
        raise_if_invalid({"product_ids": id_list_error(product_ids)})
        ticket = self._assigned_ticket(ticket_id, actor)
        ticket.add_products(self._find_products(product_ids))
        self._commit()
        return ticket

    def remove_product(self, ticket_id: int, product_id: int, actor: User) -> Ticket:
        """Remove a product from the ticket; only the assigned representative may."""
        self._reject_admin(actor)
        ticket = self._assigned_ticket(ticket_id, actor)
        ticket.remove_product(self._associated_product(ticket, product_id))
        self._commit()
        return ticket

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
