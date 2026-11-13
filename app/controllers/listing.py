"""Response shape shared by every listing endpoint (SPEC-PLT-17 and SPEC-PLT-18)."""

from collections.abc import Callable
from typing import Any

from app.domain.paging import Page


def listing_json[T](
    result: list[T] | Page[T], item_json: Callable[[T], dict[str, Any]]
) -> list[dict[str, Any]] | dict[str, Any]:
    """Serialize a plain list as an array and a `Page` as the paged object."""
    if isinstance(result, Page):
        return {
            "items": [item_json(item) for item in result.items],
            "page": result.page,
            "page_size": result.page_size,
            "total": result.total,
        }
    return [item_json(item) for item in result]
