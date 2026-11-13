"""Persistence of tickets on top of the SQLAlchemy session."""

from sqlalchemy import ColumnElement, Select, or_, select
from sqlalchemy.orm import Load, Session, selectinload

from app.db import fits_integer_column
from app.domain.milestone import Milestone
from app.domain.products import Product, ProductType
from app.domain.ticket import Ticket
from app.domain.users import User

WITH_PARTICIPANTS_AND_PRODUCTS = (
    selectinload(Ticket.client),
    selectinload(Ticket.representative),
    selectinload(Ticket.products)
    .selectinload(Product.product_type)
    .selectinload(ProductType.category),
)
WITH_MILESTONES = (selectinload(Ticket.milestones).selectinload(Milestone.author),)


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

    def list_by_client(self, client_id: int) -> list[Ticket]:
        """The tickets whose client is `client_id`, newest first."""
        return self._list_where(Ticket.client_id == client_id)

    def list_by_representative(self, representative_id: int) -> list[Ticket]:
        """The tickets assigned to `representative_id`, newest first."""
        return self._list_where(Ticket.representative_id == representative_id)

    def _list_where(self, condition: ColumnElement[bool]) -> list[Ticket]:
        statement = (
            select(Ticket)
            .options(*WITH_PARTICIPANTS_AND_PRODUCTS)
            .where(condition)
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        )
        return list(self._session.scalars(statement))
