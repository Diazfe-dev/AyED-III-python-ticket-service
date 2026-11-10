"""User management use cases: create, update, deactivate, list and authenticate."""

import re
from collections.abc import Callable
from typing import Any, Protocol

from app.domain.errors import (
    DuplicateUserError,
    InvalidCredentialsError,
    SelfDeactivationError,
    UserNotFoundError,
    ValidationError,
)
from app.domain.users import (
    DEFAULT_CHANNEL,
    NOTIFICATION_CHANNELS,
    ROLE_CLASSES,
    User,
    normalize_email,
)
from app.services.passwords import PasswordHasher

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REQUIRED = "required"
INVALID = "invalid"
TOO_SHORT = "too_short"
MIN_PASSWORD_LENGTH = 8


class UserRepository(Protocol):
    def add(self, user: User) -> None: ...

    def get(self, user_id: int) -> User | None: ...

    def find_by_email(self, email: str) -> User | None: ...

    def list_by_role(self, role: str) -> list[User]: ...


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
        _raise_if_invalid(
            {
                "name": _text_error(name),
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
        changes = _provided(name=name, email=email, preferred_channel=preferred_channel)
        _raise_if_invalid(
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

    def list_by_role(self, role: str) -> list[User]:
        return self._repository.list_by_role(role)

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


def _provided(**values: Any) -> dict[str, Any]:
    return {field: value for field, value in values.items() if value is not None}


def _raise_if_invalid(errors: dict[str, str | None]) -> None:
    fields = {field: reason for field, reason in errors.items() if reason is not None}
    if fields:
        raise ValidationError(fields)


def _text_error(value: Any) -> str | None:
    if value is None:
        return REQUIRED
    if not isinstance(value, str):
        return INVALID
    return None if value.strip() else REQUIRED


def _email_error(value: Any) -> str | None:
    error = _text_error(value)
    if error is not None:
        return error
    return None if EMAIL_PATTERN.match(normalize_email(value)) else INVALID


def _role_error(value: Any) -> str | None:
    error = _text_error(value)
    if error is not None:
        return error
    return None if value in ROLE_CLASSES else INVALID


def _password_error(value: Any) -> str | None:
    error = _text_error(value)
    if error is not None:
        return error
    return TOO_SHORT if len(value) < MIN_PASSWORD_LENGTH else None


def _channel_error(value: Any) -> str | None:
    """A missing channel is valid: it means the default on create and no change on update."""
    if value is None:
        return None
    return None if isinstance(value, str) and value in NOTIFICATION_CHANNELS else INVALID


UPDATABLE_FIELDS: dict[str, Callable[[Any], str | None]] = {
    "name": _text_error,
    "email": _email_error,
    "preferred_channel": _channel_error,
}
