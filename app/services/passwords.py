"""Password hashing behind a protocol, so services can be tested without a slow hash."""

from functools import cache
from typing import Protocol

from werkzeug.security import check_password_hash, generate_password_hash

DUMMY_PASSWORD = "dummy-password-for-unknown-users"


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...

    def dummy_hash(self) -> str:
        """A real hash of no user's password, to verify against when the user is unknown."""
        ...


class WerkzeugPasswordHasher:
    """Production hasher backed by `werkzeug.security`."""

    def hash(self, password: str) -> str:
        return generate_password_hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)

    def dummy_hash(self) -> str:
        return _werkzeug_dummy_hash()


@cache
def _werkzeug_dummy_hash() -> str:
    """Computed once per process, so a failed login costs one verify and no extra hash."""
    return generate_password_hash(DUMMY_PASSWORD)
