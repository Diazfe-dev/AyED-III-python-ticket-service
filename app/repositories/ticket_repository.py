"""Persistence of tickets on top of the SQLAlchemy session."""

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Load, Session, aliased, selectinload

from app.db import fits_integer_column
from app.domain.milestone import Milestone
from app.domain.paging import Page, PageRequest
from app.domain.products import Product, ProductType
from app.domain.state_change import StateChange
from app.domain.ticket import Ticket
from app.domain.users import User
from app.repositories.paging import fetch

WITH_PARTICIPANTS_AND_PRODUCTS = (
    selectinload(Ticket.client),
    selectinload(Ticket.representative),
    selectinload(Ticket.products)
    .selectinload(Product.product_type)
    .selectinload(ProductType.category),
)
WITH_MILESTONES = (selectinload(Ticket.milestones).selectinload(Milestone.author),)
WITH_HISTORY = (selectinload(Ticket.state_history).selectinload(StateChange.user),)


class SqlAlchemyTicketRepository:
    """Stores and finds tickets; it never commits and never deletes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, ticket: Ticket) -> None:
        """Stage the ticket and flush, so it has its id before the use case goes on."""
        self._session.add(ticket)
        self._session.flush()

    def get_visible(self, ticket_id: int, actor: User) -> Ticket | None:
        """The ticket if the actor is its client or its representative, else `None`.

        An id SQLite cannot store matches nothing, so it never reaches the query.
        """
        return self._find(ticket_id, actor, ())

    def get_visible_with_milestones(self, ticket_id: int, actor: User) -> Ticket | None:
        """Like `get_visible`, with the milestones and their authors loaded."""
        return self._find(ticket_id, actor, WITH_MILESTONES)

    def get(self, ticket_id: int) -> Ticket | None:
        """The ticket whoever its participants are, else `None` (for the `Admin`)."""
        return self._find(ticket_id, None, ())

    def get_with_milestones(self, ticket_id: int) -> Ticket | None:
        """Like `get`, with the milestones and their authors loaded."""
        return self._find(ticket_id, None, WITH_MILESTONES)

    def get_visible_with_history(self, ticket_id: int, actor: User) -> Ticket | None:
        """Like `get_visible`, with the state changes (in order) and their users loaded."""
        return self._find(ticket_id, actor, WITH_HISTORY)

    def get_with_history(self, ticket_id: int) -> Ticket | None:
        """Like `get`, with the state changes (in order) and their users loaded."""
        return self._find(ticket_id, None, WITH_HISTORY)

    def _find(
        self, ticket_id: int, participant: User | None, extra_options: tuple[Load, ...]
    ) -> Ticket | None:
        if not fits_integer_column(ticket_id):
            return None
        statement = self._ticket_statement(ticket_id, participant).options(*extra_options)
        return self._session.scalars(statement).one_or_none()

    @staticmethod
    def _ticket_statement(ticket_id: int, participant: User | None) -> Select[tuple[Ticket]]:
        statement = (
            select(Ticket).options(*WITH_PARTICIPANTS_AND_PRODUCTS).where(Ticket.id == ticket_id)
        )
        if participant is None:
            return statement
        return statement.where(
            or_(Ticket.client_id == participant.id, Ticket.representative_id == participant.id)
        )

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
        """Tickets matching every given filter, by `(created_at, id)`, newest first by default.

        `q` matches the client's name or the first message as a substring, ignoring case; `%` and
        `_` in it are literal. An id SQLite cannot store matches nothing, so the query is not run.
        """
        ids = {Ticket.client_id: client_id, Ticket.representative_id: representative_id}
        if not all(fits_integer_column(value) for value in ids.values() if value is not None):
            return _nothing(window)
        statement = select(Ticket).options(*WITH_PARTICIPANTS_AND_PRODUCTS)
        for column, value in ids.items():
            if value is not None:
                statement = statement.where(column == value)
        if state is not None:
            statement = statement.where(Ticket.state_name == state)
        if q is not None:
            statement = statement.join(_CLIENT, Ticket.client_id == _CLIENT.id).where(
                _text_match(q.casefold())
            )
        order = (
            (Ticket.created_at.asc(), Ticket.id.asc())
            if ascending
            else (Ticket.created_at.desc(), Ticket.id.desc())
        )
        statement = statement.order_by(*order)
        return fetch(self._session, statement, window)


_CLIENT = aliased(User)


def _text_match(text: str) -> ColumnElement[bool]:
    first_message = (
        select(Milestone.content)
        .where(Milestone.ticket_id == Ticket.id)
        .order_by(Milestone.created_at, Milestone.id)
        .limit(1)
        .correlate(Ticket)
        .scalar_subquery()
    )
    return or_(
        func.casefold(_CLIENT.name).contains(text, autoescape=True),
        func.casefold(first_message).contains(text, autoescape=True),
    )


def _nothing(window: PageRequest | None) -> list[Ticket] | Page[Ticket]:
    if window is None:
        return []
    return Page(items=[], page=window.page, page_size=window.page_size, total=0)
