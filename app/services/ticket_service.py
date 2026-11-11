"""Ticket use cases."""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from app.domain.products import Product
from app.domain.ticket import Ticket
from app.domain.users import Client, Representative, User
from app.services.product_service import ProductRepository
from app.services.user_service import UserRepository


class TicketRepository(Protocol):
    def add(self, ticket: Ticket) -> None: ...

    def get_visible(self, ticket_id: int, actor: User) -> Ticket | None: ...


class TicketNotifier(Protocol):
    """Extension point for the notifications area."""

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
        client_id: int,
        product_ids: list[int] | None,
        first_message: str,
        actor: Representative,
    ) -> Ticket:
        """Open a ticket for the client, assigned to the calling representative."""
        client: Client = self._users.get(client_id)
        products = self._find_products(product_ids or [])
        ticket = Ticket.open(client, actor, products, first_message, self._clock())
        self._tickets.add(ticket)
        self._commit()
        return ticket

    def _find_products(self, product_ids: list[int]) -> list[Product]:
        return self._products.get_many(list(dict.fromkeys(product_ids)))
