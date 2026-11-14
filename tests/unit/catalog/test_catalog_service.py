from dataclasses import dataclass
from typing import Any

import pytest

from app.domain.errors import (
    DuplicateProductTypeError,
    ProductTypeInUseError,
    ProductTypeNotFoundError,
    ValidationError,
)
from app.domain.products import Product, ProductType
from app.services.catalog_service import CatalogService
from tests.unit.catalog.fakes import FakeProductTypeRepository
from tests.unit.fakes import CommitSpy


@dataclass
class ServiceUnderTest:
    service: CatalogService
    product_types: FakeProductTypeRepository
    commit: CommitSpy


@pytest.fixture
def sut() -> ServiceUnderTest:
    product_types, commit = FakeProductTypeRepository(), CommitSpy()
    service = CatalogService(product_types, commit)
    return ServiceUnderTest(service, product_types, commit)


def add_type(sut: ServiceUnderTest, name: str) -> ProductType:
    product_type = ProductType(name=name)
    sut.product_types.add(product_type)
    return product_type


def test_create_product_type_stores_it_and_commits(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-25 · TC-PTY-25a"""
    product_type = sut.service.create_product_type("Notebook")

    assert product_type.name == "Notebook"
    assert sut.product_types.get(product_type.id) is product_type
    assert sut.commit.calls == 1


def test_create_product_type_with_a_taken_name_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-26 · TC-PTY-26a"""
    existing = add_type(sut, "Notebook")

    with pytest.raises(DuplicateProductTypeError):
        sut.service.create_product_type(" NOTEBOOK ")

    assert list(sut.product_types.product_types.values()) == [existing]
    assert sut.commit.calls == 0


@pytest.mark.parametrize(
    ("name", "reason"), [(None, "required"), ("", "required"), ("   ", "required"), (7, "invalid")]
)
def test_create_product_type_with_invalid_name_is_rejected(
    sut: ServiceUnderTest, name: Any, reason: str
) -> None:
    """SPEC-PTY-27 · TC-PTY-27a"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_product_type(name)

    assert raised.value.fields == {"name": reason}
    assert sut.product_types.product_types == {}
    assert sut.commit.calls == 0


MALFORMED_IDS = [True, False, 1.5, 0, -3, "abc", "-1", "0", "1.5", "", [1]]


def test_update_product_type_renames_it_and_commits(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-29 · TC-PTY-29a"""
    notebook = add_type(sut, "Notebook")

    updated = sut.service.update_product_type(notebook.id, name="Ultrabook")

    assert updated is notebook
    assert notebook.name == "Ultrabook"
    assert sut.commit.calls == 1


def test_update_product_type_to_its_own_name_in_other_case_is_allowed(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-PTY-29 · TC-PTY-29b"""
    notebook = add_type(sut, "Notebook")

    sut.service.update_product_type(notebook.id, name="NOTEBOOK")

    assert notebook.name == "NOTEBOOK"


def test_update_unknown_product_type_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-29 · TC-PTY-29c"""
    with pytest.raises(ProductTypeNotFoundError):
        sut.service.update_product_type(9999, name="X")

    assert sut.commit.calls == 0


@pytest.mark.parametrize(("name", "reason"), [("   ", "required"), (["x"], "invalid")])
def test_update_product_type_with_invalid_name_is_rejected(
    sut: ServiceUnderTest, name: Any, reason: str
) -> None:
    """SPEC-PTY-27 · TC-PTY-27b"""
    notebook = add_type(sut, "Notebook")

    with pytest.raises(ValidationError) as raised:
        sut.service.update_product_type(notebook.id, name=name)

    assert raised.value.fields == {"name": reason}
    assert notebook.name == "Notebook"
    assert sut.commit.calls == 0


def test_renaming_a_product_type_to_the_name_of_another_is_rejected(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-PTY-30 · TC-PTY-30a"""
    add_type(sut, "Notebook")
    router = add_type(sut, "Router")

    with pytest.raises(DuplicateProductTypeError):
        sut.service.update_product_type(router.id, name=" NOTEBOOK ")

    assert router.name == "Router"
    assert sut.commit.calls == 0


def test_delete_product_type_removes_it_and_commits(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-07 · TC-PTY-07a"""
    notebook = add_type(sut, "Notebook")

    sut.service.delete_product_type(notebook.id)

    assert sut.product_types.get(notebook.id) is None
    assert sut.commit.calls == 1


def test_delete_unknown_product_type_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-07 · TC-PTY-07b"""
    with pytest.raises(ProductTypeNotFoundError):
        sut.service.delete_product_type(9999)

    assert sut.commit.calls == 0


def test_delete_product_type_with_an_inactive_product_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-08 · TC-PTY-08a"""
    notebook = add_type(sut, "Notebook")
    Product(name="XPS 13", product_type=notebook, is_active=False)

    with pytest.raises(ProductTypeInUseError):
        sut.service.delete_product_type(notebook.id)

    assert sut.product_types.get(notebook.id) is notebook
    assert sut.commit.calls == 0


FLAT_NAMES = ["Router", "Notebook", "Ruteador USB", "Cámara", "50% off", "access point"]


@pytest.fixture
def flat_reference_data(sut: ServiceUnderTest) -> None:
    for name in FLAT_NAMES:
        add_type(sut, name)


@pytest.mark.usefixtures("flat_reference_data")
def test_list_product_types_returns_a_flat_list_ordered_by_name(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-31 · TC-PTY-31a"""
    found = sut.service.list_product_types()

    assert all(isinstance(product_type, ProductType) for product_type in found)
    assert [product_type.name for product_type in found] == [
        "50% off",
        "access point",
        "Cámara",
        "Notebook",
        "Router",
        "Ruteador USB",
    ]


@pytest.mark.usefixtures("flat_reference_data")
def test_list_product_types_with_q_keeps_only_names_containing_it(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-32 · TC-PTY-32a"""
    found = [product_type.name for product_type in sut.service.list_product_types(q="UTE")]
    none = sut.service.list_product_types(q="zzz")

    assert found == ["Router", "Ruteador USB"]
    assert none == []
