"""Field validation helpers shared by the services: each check returns a reason or `None`."""

from typing import Any

from app.domain.errors import ValidationError

REQUIRED = "required"
INVALID = "invalid"


def provided(**values: Any) -> dict[str, Any]:
    """The values that were given, dropping the ones left as `None`."""
    return {field: value for field, value in values.items() if value is not None}


def raise_if_invalid(errors: dict[str, str | None]) -> None:
    """Raise a `ValidationError` with every field that has a reason."""
    fields = {field: reason for field, reason in errors.items() if reason is not None}
    if fields:
        raise ValidationError(fields)


def text_error(value: Any) -> str | None:
    """A text is required: missing or blank is `required`, any other type is `invalid`."""
    if value is None:
        return REQUIRED
    if not isinstance(value, str):
        return INVALID
    return None if value.strip() else REQUIRED


def id_error(value: Any) -> str | None:
    """An id is required and must be a positive integer, as a JSON number or as ASCII digits."""
    if value is None:
        return REQUIRED
    return None if _is_positive_id(value) else INVALID


def id_list_error(value: Any) -> str | None:
    """A non-empty list of positive integer ids is required; digit text is not accepted."""
    if value is None:
        return REQUIRED
    if not isinstance(value, list) or not value:
        return INVALID
    return None if all(_is_positive_int(item) for item in value) else INVALID


def parse_id(value: Any) -> int:
    """The integer of an id that already passed `id_error` (a query string value is text)."""
    return int(value)


def _is_positive_id(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        return _digits_value(value) > 0
    return isinstance(value, int) and value > 0


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _digits_value(text: str) -> int:
    """The number written with ASCII digits, or 0 if it is not one or is too long to convert."""
    if not (text.isascii() and text.isdigit()):
        return 0
    try:
        return int(text)
    except ValueError:
        return 0
