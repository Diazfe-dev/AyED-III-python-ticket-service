"""Persistence of users on top of the SQLAlchemy session."""

from sqlalchemy import ColumnElement, func, or_, select
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

    def search(
        self,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        q: str | None = None,
        search_email: bool = True,
        window: PageRequest | None = None,
    ) -> list[User] | Page[User]:
        """Users optionally filtered by role, state and text, by name ignoring case and then id.

        `q` matches a name (and an email, unless `search_email` is off) as a substring, ignoring
        case; `%` and `_` in it are literal.
        """
        entity = ROLE_CLASSES[role] if role is not None else User
        statement = select(entity)
        if is_active is not None:
            statement = statement.where(entity.is_active == is_active)
        if q is not None:
            statement = statement.where(_text_match(entity, q.casefold(), search_email))
        statement = statement.order_by(func.casefold(entity.name), entity.id)
        return fetch(self._session, statement, window)


def _text_match(entity: type[User], text: str, search_email: bool) -> ColumnElement[bool]:
    by_name = func.casefold(entity.name).contains(text, autoescape=True)
    if not search_email:
        return by_name
    return or_(by_name, entity.email.contains(text, autoescape=True))
