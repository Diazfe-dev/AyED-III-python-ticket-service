"""Persistence of users on top of the SQLAlchemy session."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import fits_integer_column
from app.domain.errors import DuplicateUserError
from app.domain.paging import Page, PageRequest
from app.domain.users import ROLE_CLASSES, User, normalize_email
from app.repositories.paging import fetch


class SqlAlchemyUserRepository:
    """Stores and finds users; it never commits nor deletes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> None:
        """Stage the user and flush, so a UNIQUE violation surfaces here and not at commit."""
        self._session.add(user)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise DuplicateUserError() from error

    def get(self, user_id: int) -> User | None:
        """The user, or `None`; an id SQLite cannot store matches nothing."""
        if not fits_integer_column(user_id):
            return None
        return self._session.get(User, user_id)

    def find_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == normalize_email(email))
        return self._session.scalars(statement).one_or_none()

    def list_by_role(self, role: str) -> list[User]:
        """Users of one role, active or not, ordered by id."""
        role_class = ROLE_CLASSES[role]
        return list(self._session.scalars(select(role_class).order_by(role_class.id)))

    def search(
        self, *, role: str | None = None, window: PageRequest | None = None
    ) -> list[User] | Page[User]:
        """Users, active or not, optionally of one role, by name ignoring case and then id."""
        entity = ROLE_CLASSES[role] if role is not None else User
        statement = select(entity).order_by(func.casefold(entity.name), entity.id)
        return fetch(self._session, statement, window)
