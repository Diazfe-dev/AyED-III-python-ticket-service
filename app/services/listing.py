"""Listing query parameters: optional pagination (`page`, `page_size`) and search text (`q`)."""

from app.domain.paging import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageRequest
from app.services.validation import INVALID, raise_if_invalid

MAX_PAGE = 10**18
_BOOL_QUERY = {"true": True, "false": False}


def page_request(page: str | None, page_size: str | None) -> PageRequest | None:
    """The window asked for, or `None` when neither parameter was given."""
    if page is None and page_size is None:
        return None
    number = 1 if page is None else _positive(page)
    size = DEFAULT_PAGE_SIZE if page_size is None else _positive(page_size)
    if size is not None and size > MAX_PAGE_SIZE:
        size = None
    raise_if_invalid(
        {
            "page": INVALID if number is None else None,
            "page_size": INVALID if size is None else None,
        }
    )
    return PageRequest(page=min(number, MAX_PAGE), page_size=size)


def search_text(q: str | None) -> str | None:
    """The text to search, or `None` when `q` is absent, empty or only whitespace (SPEC-PLT-27)."""
    if q is None or not q.strip():
        return None
    return q


def bool_query_error(value: str | None) -> str | None:
    """`invalid` unless the query value is absent or exactly `true` or `false` (SPEC-USR-45)."""
    return None if value is None or value in _BOOL_QUERY else INVALID


def parse_bool_query(value: str | None) -> bool | None:
    """The boolean written as `true` or `false`, or `None` when the parameter was not given."""
    return None if value is None else _BOOL_QUERY[value]


def _positive(text: str) -> int | None:
    """The number written with ASCII digits and above 0, or `None`; huge ones cap at `MAX_PAGE`."""
    if not (text.isascii() and text.isdigit()):
        return None
    digits = text.lstrip("0")
    if not digits:
        return None
    if len(digits) > len(str(MAX_PAGE)):
        return MAX_PAGE
    return int(digits)
