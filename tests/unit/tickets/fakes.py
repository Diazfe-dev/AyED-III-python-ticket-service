"""In-memory test doubles for the ticket service: no Flask, no database."""

from app.domain.ticket import Ticket
from app.domain.users import User


class FakeTicketRepository:
    """List-backed repository that assigns ids like the database would."""

    def __init__(self) -> None:
        self.tickets: list[Ticket] = []

    def add(self, ticket: Ticket) -> None:
        if ticket.id is None:
            ticket.id = len(self.tickets) + 1
        self.tickets.append(ticket)

    def get_visible(self, ticket_id: int, actor: User) -> Ticket | None:
        found = (t for t in self.tickets if t.id == ticket_id)
        ticket = next(found, None)
        if ticket is None or actor not in (ticket.client, ticket.representative):
            return None
        return ticket


class FakeTicketNotifier:
    """Records every notification request instead of sending anything."""

    def __init__(self) -> None:
        self.calls: list[tuple[User, User, Ticket, str]] = []

    def notify(self, recipient: User, actor: User, ticket: Ticket, message: str) -> None:
        self.calls.append((recipient, actor, ticket, message))
