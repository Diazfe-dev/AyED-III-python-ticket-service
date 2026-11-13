"""In-memory test doubles for the ticket service: no Flask, no database."""

from app.domain.paging import Page, PageRequest
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

    def get_visible_with_history(self, ticket_id: int, actor: User) -> Ticket | None:
        return self.get_visible(ticket_id, actor)

    def get_with_history(self, ticket_id: int) -> Ticket | None:
        return self.get(ticket_id)

    def get(self, ticket_id: int) -> Ticket | None:
        return next((t for t in self.tickets if t.id == ticket_id), None)

    def get_with_milestones(self, ticket_id: int) -> Ticket | None:
        return self.get(ticket_id)

    def search(
        self,
        *,
        client_id: int | None = None,
        representative_id: int | None = None,
        state: str | None = None,
        q: str | None = None,
        ascending: bool = False,
        window: PageRequest | None = None,
    ) -> list[Ticket] | Page[Ticket]:
        matching = [
            t
            for t in self.tickets
            if client_id in (None, t.client.id)
            and representative_id in (None, t.representative.id)
            and state in (None, t.state_name)
            and (q is None or self._mentions(t, q.casefold()))
        ]
        ordered = sorted(matching, key=lambda t: (t.created_at, t.id), reverse=not ascending)
        if window is None:
            return ordered
        start = window.offset
        items = ordered[start : start + window.limit]
        return Page(items=items, page=window.page, page_size=window.page_size, total=len(ordered))

    @staticmethod
    def _mentions(ticket: Ticket, text: str) -> bool:
        first_message = min(ticket.milestones, key=lambda m: (m.created_at, m.id or 0))
        return text in ticket.client.name.casefold() or text in first_message.content.casefold()


class FakeTicketNotifier:
    """Records every notification request instead of sending anything."""

    def __init__(self) -> None:
        self.calls: list[tuple[User, User, Ticket, str]] = []

    def notify(self, recipient: User, actor: User, ticket: Ticket, message: str) -> None:
        self.calls.append((recipient, actor, ticket, message))
