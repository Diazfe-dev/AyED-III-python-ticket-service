"""Unit tests for the optional pagination parameters (SPEC-PLT-17 to 20, 24 to 26)."""

import pytest

from app.domain.errors import ValidationError
from app.domain.paging import MAX_PAGE_SIZE, PageRequest
from app.services.listing import MAX_PAGE, page_request, search_text

INVALID_VALUES = ["0", "-1", "abc", "", "1.5", " 1", "+1", "١"]


def test_page_request_with_both_values():
    """SPEC-PLT-17 · TC-PLT-17a"""
    window = page_request("2", "10")

    assert window == PageRequest(page=2, page_size=10)
    assert window.offset == 10
    assert window.limit == 10


def test_page_request_without_values_does_not_paginate():
    """SPEC-PLT-18 · TC-PLT-18a"""
    assert page_request(None, None) is None


def test_first_page_has_offset_zero():
    """SPEC-PLT-19 · TC-PLT-19a"""
    assert page_request("1", "5").offset == 0


@pytest.mark.parametrize("value", INVALID_VALUES)
def test_invalid_page_is_rejected(value):
    """SPEC-PLT-20 · TC-PLT-20a"""
    with pytest.raises(ValidationError) as error:
        page_request(value, None)

    assert error.value.fields == {"page": "invalid"}


@pytest.mark.parametrize("value", [*INVALID_VALUES, str(MAX_PAGE_SIZE + 1)])
def test_invalid_page_size_is_rejected(value):
    """SPEC-PLT-20 · TC-PLT-20b"""
    with pytest.raises(ValidationError) as error:
        page_request(None, value)

    assert error.value.fields == {"page_size": "invalid"}


def test_both_invalid_fields_are_reported_together():
    """SPEC-PLT-20 · TC-PLT-20c"""
    with pytest.raises(ValidationError) as error:
        page_request("x", "0")

    assert error.value.fields == {"page": "invalid", "page_size": "invalid"}


def test_missing_page_defaults_to_first():
    """SPEC-PLT-24 · TC-PLT-24a"""
    assert page_request(None, "5") == PageRequest(page=1, page_size=5)


def test_missing_page_size_defaults_to_twenty():
    """SPEC-PLT-25 · TC-PLT-25a"""
    assert page_request("3", None) == PageRequest(page=3, page_size=20)


def test_page_size_limit_is_one_hundred():
    """SPEC-PLT-26 · TC-PLT-26a"""
    assert page_request(None, "100").page_size == 100
    with pytest.raises(ValidationError) as error:
        page_request(None, "101")

    assert error.value.fields == {"page_size": "invalid"}


def test_huge_page_is_clamped():
    """SPEC-PLT-22 · TC-PLT-22b"""
    assert page_request("9" * 5000, "5").page == MAX_PAGE


@pytest.mark.parametrize("value", [None, "", "   ", "\t"])
def test_blank_search_text_is_treated_as_absent(value):
    """SPEC-PLT-27 · TC-PLT-27a"""
    assert search_text(value) is None


@pytest.mark.parametrize("value", ["ana", " an a "])
def test_search_text_with_content_is_returned_unchanged(value):
    """SPEC-PLT-27 · TC-PLT-27a"""
    assert search_text(value) == value
