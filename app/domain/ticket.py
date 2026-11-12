"""The ticket aggregate root."""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base
from app.domain.errors import ProductNotInTicketError
from app.domain.milestone import Milestone
from app.domain.notifications import Notification
from app.domain.products import Product
from app.domain.state_change import StateChange
from app.domain.states import STATES, State
from app.domain.types import UtcDateTime
from app.domain.users import Client, Representative, User

ticket_products = Table(
    "ticket_products",
    Base.metadata,
    Column("ticket_id", ForeignKey("tickets.id", ondelete="RESTRICT"), primary_key=True),
    Column(
        "product_id", ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True, index=True
    ),
)


class Ticket(Base):
    """A support ticket of a client, handled by one representative."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    representative_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    state_name: Mapped[str] = mapped_column(String(20), default="New")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    client: Mapped[Client] = relationship(back_populates="tickets", foreign_keys=[client_id])
    representative: Mapped[Representative] = relationship(
        back_populates="assigned_tickets", foreign_keys=[representative_id]
    )
    products: Mapped[list[Product]] = relationship(
        secondary=ticket_products, order_by=(Product.name_key, Product.id)
    )
    milestones: Mapped[list[Milestone]] = relationship(
        back_populates="ticket",
        order_by=(Milestone.created_at, Milestone.id),
        passive_deletes="all",
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="ticket",
        order_by=(Notification.created_at, Notification.id),
        passive_deletes="all",
    )
    state_history: Mapped[list[StateChange]] = relationship(
        back_populates="ticket",
        order_by=(StateChange.timestamp, StateChange.id),
        passive_deletes="all",
    )

    @classmethod
    def open(
        cls,
        client: Client,
        representative: Representative,
        products: Iterable[Product],
        first_message: str,
        now: datetime,
    ) -> "Ticket":
        """Create a `New` ticket assigned to the representative, with its first record."""
        ticket = cls(
            client=client,
            representative=representative,
            state_name="New",
            created_at=now,
            products=list(products),
        )
        ticket._append_milestone(first_message, representative, now)
        ticket.state_history.append(
            StateChange(user=representative, state_name="New", timestamp=now)
        )
        return ticket

    @property
    def state(self) -> State:
        """The lifecycle state object for the stored `state_name` (read-only)."""
        return STATES[self.state_name]

    def add_products(self, products: Iterable[Product]) -> None:
        """Associate the products, ignoring the ones the ticket already has."""
        for product in products:
            if product not in self.products:
                self.products.append(product)

    def remove_product(self, product: Product) -> None:
        """Drop the association only; the product itself stays in the catalog."""
        if product not in self.products:
            raise ProductNotInTicketError()
        self.products.remove(product)

    def add_milestone(self, content: str, author: User, now: datetime) -> Milestone:
        """Record a message on the ticket; the current state decides whether it is accepted."""
        return self.state.add_milestone(self, content, author, now)

    def _append_milestone(self, content: str, author: User, now: datetime) -> Milestone:
        """The only place that builds a `Milestone`."""
        milestone = Milestone(author=author, content=content, created_at=now)
        self.milestones.append(milestone)
        return milestone

    def record_notification(
        self, recipient: User, channel: str, message: str, now: datetime
    ) -> Notification:
        """Record a notification that was sent."""
        return self._append_notification(recipient, channel, message, now, "sent", None)

    def record_failed_notification(
        self, recipient: User, channel: str, message: str, now: datetime, error: str
    ) -> Notification:
        """Record a notification whose sending failed, with the error text."""
        return self._append_notification(recipient, channel, message, now, "failed", error)

    def _append_notification(
        self,
        recipient: User,
        channel: str,
        message: str,
        now: datetime,
        status: str,
        error: str | None,
    ) -> Notification:
        """The only place that builds a `Notification`."""
        notification = Notification(
            recipient=recipient,
            channel=channel,
            message=message,
            created_at=now,
            status=status,
            error=error,
        )
        self.notifications.append(notification)
        return notification

    def close(self, user: User, now: datetime) -> None:
        self.state.close(self, user, now)

    def reopen(self, user: User, now: datetime) -> None:
        self.state.reopen(self, user, now)

    def start_progress(self, user: User, now: datetime) -> None:
        self.state.in_progress(self, user, now)

    def request_progress(self, user: User, now: datetime) -> bool:
        """Move to `InProgress` only if the state allows it; tells whether the state changed."""
        return self.state.request_progress(self, user, now)

    def _enter(self, state_class: type[State], user: User, now: datetime) -> None:
        """Move to the state and record it; the only place that changes `state_name`."""
        self.state_name = state_class.name
        self.state_history.append(
            StateChange(user=user, state_name=state_class.name, timestamp=now)
        )
