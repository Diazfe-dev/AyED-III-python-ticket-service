"""Translation of domain and HTTP errors into JSON HTTP responses."""

import json
from collections.abc import Callable

from flask import Flask, jsonify
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException, InternalServerError, MethodNotAllowed, NotFound

from app.domain.errors import (
    CategoryInUseError,
    CategoryNotFoundError,
    DomainError,
    DuplicateCategoryError,
    DuplicateProductError,
    DuplicateProductTypeError,
    DuplicateUserError,
    InvalidClientError,
    InvalidCredentialsError,
    InvalidProductError,
    InvalidTransitionError,
    PermissionDeniedError,
    ProductNotFoundError,
    ProductNotInTicketError,
    ProductTypeInUseError,
    ProductTypeNotFoundError,
    SelfDeactivationError,
    TicketClosedError,
    TicketNotFoundError,
    UserNotFoundError,
    ValidationError,
)

ERROR_RESPONSES: dict[type[DomainError], tuple[int, str]] = {
    ValidationError: (400, "validation_error"),
    InvalidCredentialsError: (401, "invalid_credentials"),
    PermissionDeniedError: (403, "forbidden"),
    InvalidClientError: (400, "invalid_client"),
    InvalidProductError: (400, "invalid_product"),
    UserNotFoundError: (404, "user_not_found"),
    CategoryNotFoundError: (404, "category_not_found"),
    ProductTypeNotFoundError: (404, "product_type_not_found"),
    ProductNotFoundError: (404, "product_not_found"),
    TicketNotFoundError: (404, "ticket_not_found"),
    ProductNotInTicketError: (404, "product_not_in_ticket"),
    InvalidTransitionError: (409, "invalid_transition"),
    TicketClosedError: (409, "ticket_closed"),
    DuplicateUserError: (409, "duplicate_email"),
    SelfDeactivationError: (409, "self_deactivation"),
    DuplicateCategoryError: (409, "duplicate_category"),
    CategoryInUseError: (409, "category_in_use"),
    DuplicateProductTypeError: (409, "duplicate_product_type"),
    DuplicateProductError: (409, "duplicate_product"),
    ProductTypeInUseError: (409, "product_type_in_use"),
}


# `InternalServerError` and not `Exception`: Flask calls it once the error escaped the view, so
# the teardown still receives the exception and rolls back. Its body never carries the message.
HTTP_ERROR_RESPONSES: dict[type[HTTPException], str] = {
    NotFound: "not_found",
    MethodNotAllowed: "method_not_allowed",
    InternalServerError: "internal_error",
}


def register_error_handlers(app: Flask) -> None:
    for error_class, (status, code) in ERROR_RESPONSES.items():
        app.register_error_handler(error_class, _json_error(status, code))
    for http_error_class, http_code in HTTP_ERROR_RESPONSES.items():
        app.register_error_handler(http_error_class, _json_http_error(http_code))


def _json_error(status: int, code: str) -> Callable[[DomainError], ResponseReturnValue]:
    def handle(error: DomainError) -> ResponseReturnValue:
        return jsonify(error=code, **error.details), status

    return handle


def _json_http_error(code: str) -> Callable[[HTTPException], ResponseReturnValue]:
    """Keep werkzeug's status and headers (such as `Allow`) and replace the HTML body."""

    def handle(error: HTTPException) -> ResponseReturnValue:
        response = error.get_response()
        response.set_data(json.dumps({"error": code}))
        response.mimetype = "application/json"
        return response

    return handle
