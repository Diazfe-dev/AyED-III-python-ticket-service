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


class DuplicateCategoryError(DomainError):
    message = "A category with this name already exists."


class CategoryInUseError(DomainError):
    message = "The category has product types and cannot be deleted."


class DuplicateProductTypeError(DomainError):
    message = "A product type with this name already exists in the category."


class CategoryNotFoundError(DomainError):
    message = "Category not found."


class ProductTypeNotFoundError(DomainError):
    message = "Product type not found."


class DuplicateProductError(DomainError):
    message = "A product with this name already exists in the product type."


class ProductTypeInUseError(DomainError):
    message = "The product type has products and cannot be deleted."


class ProductNotFoundError(DomainError):
    message = "Product not found."


class InvalidTransitionError(DomainError):
    pass


class ProductNotInTicketError(DomainError):
    pass


class ImmutableRecordError(DomainError):
    message = "This record is immutable and cannot be modified or deleted."


class PermissionDeniedError(DomainError):
    message = "You do not have permission to perform this operation."


class InvalidClientError(DomainError):
    message = "The client does not exist or is not an active client."


class InvalidProductError(DomainError):
    message = "A product does not exist or is not active."


class TicketNotFoundError(DomainError):
    message = "Ticket not found."


class TicketClosedError(DomainError):
    message = "The ticket is closed; reopen it before adding milestones."
