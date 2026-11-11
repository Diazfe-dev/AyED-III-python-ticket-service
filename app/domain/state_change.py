"""State changes: the audit record of every transition of a ticket."""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base
from app.domain.immutable import make_immutable
from app.domain.types import UtcDateTime
from app.domain.users import User


class StateChange(Base):
    """Who moved a ticket to which state and when; it is only created through the ticket."""

    __tablename__ = "state_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    state_name: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(UtcDateTime)
    ticket: Mapped["Ticket"] = relationship(back_populates="state_history")  # noqa: F821
    user: Mapped[User] = relationship()


make_immutable(StateChange)
