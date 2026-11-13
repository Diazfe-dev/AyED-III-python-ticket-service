"""Unit tests for the listing response shape (SPEC-PLT-17 and SPEC-PLT-18)."""

from app.controllers.listing import listing_json
from app.domain.paging import Page


def item_json(value: str) -> dict[str, str]:
    return {"name": value}


def test_page_serializes_to_an_object_with_four_keys() -> None:
    """SPEC-PLT-17 · TC-PLT-17b"""
    page = Page(items=["a", "b"], page=2, page_size=2, total=5)

    body = listing_json(page, item_json)

    assert body == {
        "items": [{"name": "a"}, {"name": "b"}],
        "page": 2,
        "page_size": 2,
        "total": 5,
    }
    assert set(body) == {"items", "page", "page_size", "total"}


def test_list_serializes_to_a_flat_array() -> None:
    """SPEC-PLT-18 · TC-PLT-18c"""
    body = listing_json(["a", "b"], item_json)

    assert body == [{"name": "a"}, {"name": "b"}]
    assert isinstance(body, list)
