"""Lifecycle states of a ticket (State pattern); the states hold no data of their own."""

from datetime import datetime
from typing import TYPE_CHECKING

from app.domain.errors import InvalidTransitionError, TicketClosedError
from app.domain.milestone import Milestone
from app.domain.users import User

if TYPE_CHECKING:
    from app.domain.ticket import Ticket


class State:
    """Rejects every transition; each concrete state overrides the ones it allows."""

    name: str

    def close(self, ticket: "Ticket", user: User, now: datetime) -> None:
        raise InvalidTransitionError()

    def reopen(self, ticket: "Ticket", user: User, now: datetime) -> None:
        raise InvalidTransitionError()

    def in_progress(self, ticket: "Ticket", user: User, now: datetime) -> None:
        raise InvalidTransitionError()

    def request_progress(self, ticket: "Ticket", user: User, now: datetime) -> None:
        """Does nothing by default; only `New` turns the request into a transition."""

    def add_milestone(
        self, ticket: "Ticket", content: str, author: User, now: datetime
    ) -> Milestone:
        """Accepts by default; only the states that refuse milestones override it."""
        return ticket._append_milestone(content, author, now)


class NewState(State):
    name = "New"

    def in_progress(self, ticket: "Ticket", user: User, now: datetime) -> None:
        ticket._enter(InProgressState, user, now)

    def request_progress(self, ticket: "Ticket", user: User, now: datetime) -> None:
        self.in_progress(ticket, user, now)

    def close(self, ticket: "Ticket", user: User, now: datetime) -> None:
        ticket._enter(ClosedState, user, now)


class InProgressState(State):
    name = "InProgress"

    def close(self, ticket: "Ticket", user: User, now: datetime) -> None:
        ticket._enter(ClosedState, user, now)


class ClosedState(State):
    name = "Closed"

    def reopen(self, ticket: "Ticket", user: User, now: datetime) -> None:
        ticket._enter(InProgressState, user, now)

    def add_milestone(
        self, ticket: "Ticket", content: str, author: User, now: datetime
    ) -> Milestone:
        raise TicketClosedError()


STATES: dict[str, State] = {
    state_class.name: state_class() for state_class in (NewState, InProgressState, ClosedState)
}
