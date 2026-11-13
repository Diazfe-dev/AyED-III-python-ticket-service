"""User management use cases: create, update, deactivate, list and authenticate."""

import re
from collections.abc import Callable
from typing import Any, Protocol

from app.domain.errors import (
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    PermissionDeniedError,
    SelfDeactivationError,
    UserNotFoundError,
    ValidationError,
)
from app.domain.paging import Page, PageRequest
from app.domain.users import (
    DEFAULT_CHANNEL,
    NOTIFICATION_CHANNELS,
    ROLE_CLASSES,
    User,
    normalize_email,
)
from app.services.listing import bool_query_error, page_request, parse_bool_query, search_text
from app.services.passwords import PasswordHasher
from app.services.validation import INVALID, REQUIRED, provided, raise_if_invalid, text_error

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TOO_SHORT = "too_short"
MIN_PASSWORD_LENGTH = 8


class UserRepository(Protocol):
    def add(self, user: User) -> None: ...

    def get(self, user_id: int) -> User | None: ...

    def find_by_email(self, email: str) -> User | None: ...

    def search(
        self,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        q: str | None = None,
        search_email: bool = True,
        window: PageRequest | None = None,
    ) -> list[User] | Page[User]: ...


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        hasher: PasswordHasher,
        commit: Callable[[], None],
    ) -> None:
        self._repository = repository
        self._hasher = hasher
        self._commit = commit

    def create_user(
        self,
        name: Any,
        email: Any,
        role: Any,
        password: Any,
        preferred_channel: Any = None,
    ) -> User:
        """Create an active user; input comes unchecked from the caller and is validated here."""
        raise_if_invalid(
            {
                "name": text_error(name),
                "email": _email_error(email),
                "role": _role_error(role),
                "password": _password_error(password),
                "preferred_channel": _channel_error(preferred_channel),
            }
        )
        self._ensure_email_is_free(email)
        user = ROLE_CLASSES[role](
            name=name,
            email=email,
            password_hash=self._hasher.hash(password),
            preferred_channel=DEFAULT_CHANNEL if preferred_channel is None else preferred_channel,
            is_active=True,
        )
        self._repository.add(user)
        self._commit()
        return user

    def update_user(
        self,
        user_id: int,
        *,
        name: Any = None,
        email: Any = None,
        preferred_channel: Any = None,
    ) -> User:
        """Change the given data of a user; a field left as `None` keeps its value."""
        user = self._get_existing(user_id)
        changes = provided(name=name, email=email, preferred_channel=preferred_channel)
        raise_if_invalid(
            {field: UPDATABLE_FIELDS[field](value) for field, value in changes.items()}
        )
        if "email" in changes:
            self._ensure_email_is_free(changes["email"], owner=user)
        for field, value in changes.items():
            setattr(user, field, value)
        self._repository.add(user)
        self._commit()
        return user

    def deactivate_user(self, user_id: int, actor: User) -> User:
        """Logical deletion of another user; the actor cannot deactivate itself."""
        if user_id == actor.id:
            raise SelfDeactivationError()
        user = self._get_existing(user_id)
        user.deactivate()
        self._commit()
        return user

    def activate_user(self, user_id: int) -> User:
        """Reactivate a user; activating an active one is not an error."""
        user = self._get_existing(user_id)
        user.activate()
        self._commit()
        return user

    def change_own_password(self, actor: User, current_password: Any, new_password: Any) -> None:
        """Replace the actor's password; the current one must match (checked after the format)."""
        raise_if_invalid(
            {
                "current_password": _current_password_error(current_password),
                "new_password": _password_error(new_password),
            }
        )
        if not self._hasher.verify(actor.password_hash, current_password):
            raise InvalidCurrentPasswordError()
        actor.password_hash = self._hasher.hash(new_password)
        self._commit()

    def reset_password(self, user_id: int, new_password: Any) -> None:
        """Set another user's password without asking for the previous one."""
        user = self._get_existing(user_id)
        raise_if_invalid({"new_password": _password_error(new_password)})
        user.password_hash = self._hasher.hash(new_password)
        self._commit()

    def list_users(
        self,
        role: str | None = None,
        is_active: str | None = None,
        q: str | None = None,
        page: str | None = None,
        page_size: str | None = None,
    ) -> list[User] | Page[User]:
        """Users of every role or of one, by name; the query values come as text and are checked."""
        window = _checked_listing(is_active, page, page_size)
        return self._repository.search(
            role=role, is_active=parse_bool_query(is_active), q=search_text(q), window=window
        )

    def list_clients(
        self,
        actor: User,
        is_active: str | None = None,
        q: str | None = None,
        page: str | None = None,
        page_size: str | None = None,
    ) -> list[User] | Page[User]:
        """Clients as the actor may see them: an admin sees all, a representative only active ones.

        The role check goes first, then the format, then the representative's `is_active` ban.
        """
        if actor.role == "Client":
            raise PermissionDeniedError()
        window = _checked_listing(is_active, page, page_size)
        if actor.role == "Representative":
            if is_active is not None:
                raise PermissionDeniedError()
            return self._repository.search(
                role="Client", is_active=True, q=search_text(q), search_email=False, window=window
            )
        return self._repository.search(
            role="Client", is_active=parse_bool_query(is_active), q=search_text(q), window=window
        )

    def authenticate(self, email: Any, password: Any) -> User:
        """Return the active user with these credentials; never tell which check failed."""
        if not isinstance(email, str) or not isinstance(password, str):
            raise InvalidCredentialsError()
        user = self._repository.find_by_email(email)
        if user is None or not user.is_active:
            self._hasher.verify(self._hasher.dummy_hash(), password)
            raise InvalidCredentialsError()
        if not self._hasher.verify(user.password_hash, password):
            raise InvalidCredentialsError()
        return user

    def find_active_user(self, user_id: int) -> User | None:
        """The user behind a session, or `None` if it no longer exists or was deactivated."""
        user = self._repository.get(user_id)
        return user if user is not None and user.is_active else None

    def _get_existing(self, user_id: int) -> User:
        user = self._repository.get(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    def _ensure_email_is_free(self, email: str, owner: User | None = None) -> None:
        """Reject an email used by any other user, active or not (RNF 3)."""
        holder = self._repository.find_by_email(email)
        if holder is not None and holder is not owner:
            raise DuplicateUserError()


def _checked_listing(
    is_active: str | None, page: str | None, page_size: str | None
) -> PageRequest | None:
    """The window asked for; `is_active` and the pagination are validated together."""
    errors: dict[str, str | None] = {"is_active": bool_query_error(is_active)}
    window = None
    try:
        window = page_request(page, page_size)
    except ValidationError as error:
        errors.update(error.fields)
    raise_if_invalid(errors)
    return window


def _email_error(value: Any) -> str | None:
    error = text_error(value)
    if error is not None:
        return error
    return None if EMAIL_PATTERN.match(normalize_email(value)) else INVALID


def _role_error(value: Any) -> str | None:
    error = text_error(value)
    if error is not None:
        return error
    return None if value in ROLE_CLASSES else INVALID


def _password_error(value: Any) -> str | None:
    error = text_error(value)
    if error is not None:
        return error
    return TOO_SHORT if len(value) < MIN_PASSWORD_LENGTH else None


def _current_password_error(value: Any) -> str | None:
    """Any text is a possible current password; only its presence and type are checked."""
    if value is None:
        return REQUIRED
    return None if isinstance(value, str) else INVALID


def _channel_error(value: Any) -> str | None:
    """A missing channel is valid: it means the default on create and no change on update."""
    if value is None:
        return None
    return None if isinstance(value, str) and value in NOTIFICATION_CHANNELS else INVALID


UPDATABLE_FIELDS: dict[str, Callable[[Any], str | None]] = {
    "name": text_error,
    "email": _email_error,
    "preferred_channel": _channel_error,
}
