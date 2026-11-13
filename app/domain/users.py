"""Users of the system and their roles, mapped with single-table inheritance."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.domain.base import Base

NOTIFICATION_CHANNELS = frozenset({"mail", "whatsapp"})
DEFAULT_CHANNEL = "mail"


def normalize_email(email: str) -> str:
    """Canonical form of an email: no surrounding spaces and lowercase."""
    return email.strip().lower()


class User(Base):
    """Common data of every user; the `role` column tells which subclass a row is."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    preferred_channel: Mapped[str] = mapped_column(String(20), default=DEFAULT_CHANNEL)
    is_active: Mapped[bool] = mapped_column(default=True)

    __mapper_args__ = {"polymorphic_on": "role"}

    @validates("email")
    def _normalize_email(self, _key: str, email: str) -> str:
        return normalize_email(email)

    def deactivate(self) -> None:
        """Logical deletion: the row and its history are kept."""
        self.is_active = False

    def activate(self) -> None:
        """Reactivation: mirror of `deactivate`."""
        self.is_active = True


class Admin(User):
    __mapper_args__ = {"polymorphic_identity": "Admin"}


class Representative(User):
    __mapper_args__ = {"polymorphic_identity": "Representative"}

    assigned_tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        "Ticket",
        back_populates="representative",
        foreign_keys="Ticket.representative_id",
        passive_deletes="all",
    )


class Client(User):
    __mapper_args__ = {"polymorphic_identity": "Client"}

    tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        "Ticket",
        back_populates="client",
        foreign_keys="Ticket.client_id",
        passive_deletes="all",
    )


ROLE_CLASSES: dict[str, type[User]] = {
    "Admin": Admin,
    "Representative": Representative,
    "Client": Client,
}
