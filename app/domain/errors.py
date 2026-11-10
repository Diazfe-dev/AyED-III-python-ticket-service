"""Domain exceptions; controllers and the CLI translate them for their callers."""

from typing import Any


class DomainError(Exception):
    """Base of every business rule violation."""

    message = "Domain rule violated."

    def __init__(self) -> None:
        super().__init__(self.message)
        self.details: dict[str, Any] = {}


class ValidationError(DomainError):
    """Invalid input; `fields` maps each invalid field to its reason."""

    message = "Invalid fields."

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__()
        self.fields = fields
        self.details = {"fields": fields}

    def __str__(self) -> str:
        reasons = ", ".join(f"{field} ({reason})" for field, reason in self.fields.items())
        return f"{self.message[:-1]}: {reasons}."


class DuplicateUserError(DomainError):
    message = "A user with this email already exists."


class UserNotFoundError(DomainError):
    message = "User not found."


class SelfDeactivationError(DomainError):
    message = "An administrator cannot deactivate their own user."


class InvalidCredentialsError(DomainError):
    """Same error for an unknown email, a wrong password or an inactive user."""

    message = "Invalid credentials."
