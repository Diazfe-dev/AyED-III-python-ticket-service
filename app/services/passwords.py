"""Password hashing behind a protocol, so services can be tested without a slow hash."""

from typing import Protocol

from werkzeug.security import check_password_hash, generate_password_hash


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...


class WerkzeugPasswordHasher:
    """Production hasher backed by `werkzeug.security`."""

    def hash(self, password: str) -> str:
        return generate_password_hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)
