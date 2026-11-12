"""Notifications: the records of what the system sent to a user about a ticket."""

from datetime import datetime
from typing import Protocol

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base
from app.domain.types import UtcDateTime
from app.domain.users import User


class Notification(Base):
    """A notification sent (or failed) to a user; it is only created through the ticket."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("status IN ('sent', 'failed')", name="notifications_status_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="RESTRICT"), index=True
    )
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    channel: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    status: Mapped[str] = mapped_column(String(10))
    error: Mapped[str | None] = mapped_column(Text, default=None)
    ticket: Mapped["Ticket"] = relationship(back_populates="notifications")  # noqa: F821
    recipient: Mapped[User] = relationship()


class NotificationStrategy(Protocol):
    """How a notification reaches its recipient; a failure is a `NotificationError`."""

    def send(self, recipient: User, message: str) -> None: ...


class MailNotification:
    """Simulated mail delivery: the record the service keeps is the delivery."""

    def send(self, recipient: User, message: str) -> None:
        return None


class WhatsappNotification:
    """Simulated WhatsApp delivery: the record the service keeps is the delivery."""

    def send(self, recipient: User, message: str) -> None:
        return None


def default_strategies() -> dict[str, NotificationStrategy]:
    """One strategy per notification channel."""
    return {"mail": MailNotification(), "whatsapp": WhatsappNotification()}
