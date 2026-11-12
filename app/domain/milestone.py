"""Milestones: the chronological entries of a ticket."""

from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base
from app.domain.immutable import make_immutable
from app.domain.types import UtcDateTime
from app.domain.users import User


class Milestone(Base):
    """A message in the history of a ticket; it is only created through the ticket."""

    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="RESTRICT"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    ticket: Mapped["Ticket"] = relationship(back_populates="milestones")  # noqa: F821
    author: Mapped[User] = relationship()


make_immutable(Milestone)
