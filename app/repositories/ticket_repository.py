"""Persistence of tickets on top of the SQLAlchemy session."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import fits_integer_column
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
        if not fits_integer_column(ticket_id):
            return None
        statement = (
            select(Ticket)
            .options(*WITH_PARTICIPANTS_AND_PRODUCTS)
            .where(
                Ticket.id == ticket_id,
                or_(Ticket.client_id == actor.id, Ticket.representative_id == actor.id),
            )
        )
        return self._session.scalars(statement).one_or_none()
