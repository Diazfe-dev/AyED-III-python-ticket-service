"""In-memory test doubles for the ticket service: no Flask, no database."""

from collections.abc import Iterable

from app.domain.ticket import Ticket
from app.domain.users import User


class FakeTicketRepository:
    """List-backed repository that assigns ids like the database would."""

    def __init__(self) -> None:
        self.tickets: list[Ticket] = []
        self.visible_lookups: list[int] = []

    def add(self, ticket: Ticket) -> None:
        if ticket.id is None:
            ticket.id = len(self.tickets) + 1
        self.tickets.append(ticket)

    def get_visible(self, ticket_id: int, actor: User) -> Ticket | None:
        self.visible_lookups.append(ticket_id)
        found = (t for t in self.tickets if t.id == ticket_id)
        ticket = next(found, None)
        if ticket is None or actor not in (ticket.client, ticket.representative):
            return None
        return ticket

    def get_visible_with_milestones(self, ticket_id: int, actor: User) -> Ticket | None:
        return self.get_visible(ticket_id, actor)

    def get(self, ticket_id: int) -> Ticket | None:
        return next((t for t in self.tickets if t.id == ticket_id), None)

    def get_with_milestones(self, ticket_id: int) -> Ticket | None:
        return self.get(ticket_id)

    def list_by_client(self, client_id: int) -> list[Ticket]:
        return self._newest_first(t for t in self.tickets if t.client.id == client_id)

    def list_by_representative(self, representative_id: int) -> list[Ticket]:
        return self._newest_first(
            t for t in self.tickets if t.representative.id == representative_id
        )

    @staticmethod
    def _newest_first(tickets: Iterable[Ticket]) -> list[Ticket]:
        return sorted(tickets, key=lambda t: (t.created_at, t.id), reverse=True)


class FakeTicketNotifier:
    """Records every notification request instead of sending anything."""

    def __init__(self) -> None:
        self.calls: list[tuple[User, User, Ticket, str]] = []

    def notify(self, recipient: User, actor: User, ticket: Ticket, message: str) -> None:
        self.calls.append((recipient, actor, ticket, message))
