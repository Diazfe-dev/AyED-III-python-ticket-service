"""Translation of domain exceptions into JSON HTTP responses."""

from collections.abc import Callable

from flask import Flask, jsonify
from flask.typing import ResponseReturnValue

from app.domain.errors import (
    CategoryInUseError,
    CategoryNotFoundError,
    DomainError,
    DuplicateCategoryError,
    DuplicateProductTypeError,
    DuplicateUserError,
    InvalidCredentialsError,
    ProductTypeNotFoundError,
    SelfDeactivationError,
    UserNotFoundError,
    ValidationError,
)

ERROR_RESPONSES: dict[type[DomainError], tuple[int, str]] = {
    ValidationError: (400, "validation_error"),
    InvalidCredentialsError: (401, "invalid_credentials"),
    UserNotFoundError: (404, "user_not_found"),
    CategoryNotFoundError: (404, "category_not_found"),
    ProductTypeNotFoundError: (404, "product_type_not_found"),
    DuplicateUserError: (409, "duplicate_email"),
    SelfDeactivationError: (409, "self_deactivation"),
    DuplicateCategoryError: (409, "duplicate_category"),
    CategoryInUseError: (409, "category_in_use"),
    DuplicateProductTypeError: (409, "duplicate_product_type"),
}


def register_error_handlers(app: Flask) -> None:
    for error_class, (status, code) in ERROR_RESPONSES.items():
        app.register_error_handler(error_class, _json_error(status, code))


def _json_error(status: int, code: str) -> Callable[[DomainError], ResponseReturnValue]:
    def handle(error: DomainError) -> ResponseReturnValue:
        return jsonify(error=code, **error.details), status

    return handle
