from dataclasses import dataclass
from typing import Any

import pytest

from app.domain.errors import (
    CategoryInUseError,
    CategoryNotFoundError,
    DuplicateCategoryError,
    DuplicateProductTypeError,
    ProductTypeInUseError,
    ProductTypeNotFoundError,
    ValidationError,
)
from app.domain.products import Category, Product, ProductType
from app.services.catalog_service import CatalogService, CategoryGroup
from tests.unit.catalog.fakes import FakeCategoryRepository, FakeProductTypeRepository
from tests.unit.fakes import CommitSpy


@dataclass
class ServiceUnderTest:
    service: CatalogService
    categories: FakeCategoryRepository
    product_types: FakeProductTypeRepository
    commit: CommitSpy


@pytest.fixture
def sut() -> ServiceUnderTest:
    categories, product_types, commit = (
        FakeCategoryRepository(),
        FakeProductTypeRepository(),
        CommitSpy(),
    )
    service = CatalogService(categories, product_types, commit)
    return ServiceUnderTest(service, categories, product_types, commit)


def test_create_category_stores_it_and_commits(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-01 · TC-PTY-01a"""
    category = sut.service.create_category("Hardware")

    assert category.name == "Hardware"
    assert sut.categories.get(category.id) is category
    assert sut.commit.calls == 1


@pytest.mark.parametrize("name", [None, "", "   "])
def test_create_category_without_name_is_rejected(sut: ServiceUnderTest, name: Any) -> None:
    """SPEC-PTY-15 · TC-PTY-15a"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_category(name)

    assert raised.value.fields == {"name": "required"}
    assert sut.categories.categories == {}
    assert sut.commit.calls == 0


@pytest.mark.parametrize("name", [123, ["Hardware"], {"name": "x"}])
def test_create_category_with_non_text_name_is_rejected(sut: ServiceUnderTest, name: Any) -> None:
    """SPEC-PTY-15 · TC-PTY-15b"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_category(name)

    assert raised.value.fields == {"name": "invalid"}
    assert sut.commit.calls == 0


def test_create_category_with_a_taken_name_in_other_case_is_rejected(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-PTY-02 · TC-PTY-02c"""
    existing = sut.service.create_category("Hardware")

    with pytest.raises(DuplicateCategoryError):
        sut.service.create_category(" HARDWARE ")

    assert list(sut.categories.categories.values()) == [existing]
    assert sut.commit.calls == 1


def test_update_category_to_a_name_taken_by_another_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-02 · TC-PTY-02d"""
    sut.service.create_category("Hardware")
    redes = sut.service.create_category("Redes")

    with pytest.raises(DuplicateCategoryError):
        sut.service.update_category(redes.id, name="hardware")

    assert redes.name == "Redes"
    assert sut.commit.calls == 2


def test_update_category_renames_it_and_commits(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-12 · TC-PTY-12a"""
    category = sut.service.create_category("Hardware")

    updated = sut.service.update_category(category.id, name="Redes")

    assert updated is category
    assert category.name == "Redes"
    assert sut.commit.calls == 2


def test_update_category_to_its_own_name_in_other_case_is_allowed(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-12 · TC-PTY-12b"""
    category = sut.service.create_category("Hardware")

    sut.service.update_category(category.id, name="HARDWARE")

    assert category.name == "HARDWARE"


def test_update_unknown_category_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-12 · TC-PTY-12c"""
    with pytest.raises(CategoryNotFoundError):
        sut.service.update_category(9999, name="Redes")

    assert sut.commit.calls == 0


@pytest.mark.parametrize(("name", "reason"), [("   ", "required"), (5, "invalid")])
def test_update_category_with_invalid_name_is_rejected(
    sut: ServiceUnderTest, name: Any, reason: str
) -> None:
    """SPEC-PTY-15 · TC-PTY-15c"""
    category = sut.service.create_category("Hardware")

    with pytest.raises(ValidationError) as raised:
        sut.service.update_category(category.id, name=name)

    assert raised.value.fields == {"name": reason}
    assert category.name == "Hardware"
    assert sut.commit.calls == 1


def test_delete_category_without_types_removes_it_and_commits(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-13 · TC-PTY-13a"""
    category = sut.service.create_category("Hardware")

    sut.service.delete_category(category.id)

    assert sut.categories.get(category.id) is None
    assert sut.commit.calls == 2


def test_delete_unknown_category_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-13 · TC-PTY-13b"""
    with pytest.raises(CategoryNotFoundError):
        sut.service.delete_category(9999)

    assert sut.commit.calls == 0


def test_delete_category_with_types_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-14 · TC-PTY-14a"""
    category = sut.service.create_category("Hardware")
    sut.product_types.add(ProductType(name="Notebook", category=category))

    with pytest.raises(CategoryInUseError):
        sut.service.delete_category(category.id)

    assert sut.categories.get(category.id) is category
    assert sut.commit.calls == 1


def test_list_categories_orders_them_by_name_ignoring_case(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-17 · TC-PTY-17b"""
    for name in ["redes", "Audio", "hardware"]:
        sut.service.create_category(name)

    names = [category.name for category in sut.service.list_categories()]

    assert names == ["Audio", "hardware", "redes"]


@pytest.fixture
def hardware(sut: ServiceUnderTest) -> Category:
    category = Category(name="Hardware")
    sut.categories.add(category)
    return category


@pytest.fixture
def office(sut: ServiceUnderTest) -> Category:
    category = Category(name="Oficina")
    sut.categories.add(category)
    return category


def add_type(sut: ServiceUnderTest, name: str, category: Category) -> ProductType:
    product_type = ProductType(name=name, category=category)
    sut.product_types.add(product_type)
    return product_type


def test_create_product_type_stores_it_in_its_category(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-03 · TC-PTY-03a"""
    product_type = sut.service.create_product_type("Notebook", hardware.id)

    assert product_type.category is hardware
    assert sut.product_types.get(product_type.id) is product_type
    assert sut.commit.calls == 1


def test_create_product_type_in_unknown_category_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-04 · TC-PTY-04a"""
    with pytest.raises(CategoryNotFoundError):
        sut.service.create_product_type("Notebook", 9999)

    assert sut.product_types.product_types == {}
    assert sut.commit.calls == 0


def test_create_product_type_with_a_taken_name_in_the_category_is_rejected(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-05 · TC-PTY-05a"""
    existing = add_type(sut, "Notebook", hardware)

    with pytest.raises(DuplicateProductTypeError):
        sut.service.create_product_type("NOTEBOOK", hardware.id)

    assert list(sut.product_types.product_types.values()) == [existing]
    assert sut.commit.calls == 0


def test_create_product_type_may_repeat_a_name_of_another_category(
    sut: ServiceUnderTest, hardware: Category, office: Category
) -> None:
    """SPEC-PTY-05 · TC-PTY-05b"""
    add_type(sut, "Notebook", hardware)

    product_type = sut.service.create_product_type("Notebook", office.id)

    assert product_type.category is office
    assert sut.commit.calls == 1


@pytest.mark.parametrize(("name", "reason"), [("", "required"), (7, "invalid")])
def test_create_product_type_with_invalid_name_is_rejected(
    sut: ServiceUnderTest, hardware: Category, name: Any, reason: str
) -> None:
    """SPEC-PTY-15 · TC-PTY-15d"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_product_type(name, hardware.id)

    assert raised.value.fields == {"name": reason}
    assert sut.product_types.product_types == {}
    assert sut.commit.calls == 0


MALFORMED_IDS = [True, False, 1.5, 0, -3, "abc", "-1", "0", "1.5", "", [1]]


@pytest.mark.usefixtures("hardware")
@pytest.mark.parametrize("category_id", MALFORMED_IDS)
def test_create_product_type_with_malformed_category_id_is_rejected(
    sut: ServiceUnderTest, category_id: Any
) -> None:
    """SPEC-PTY-20 · TC-PTY-20a"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_product_type("Notebook", category_id)

    assert raised.value.fields == {"category_id": "invalid"}
    assert sut.product_types.product_types == {}
    assert sut.commit.calls == 0


@pytest.mark.parametrize(
    ("name", "fields"),
    [
        ("Notebook", {"category_id": "required"}),
        ("", {"name": "required", "category_id": "required"}),
    ],
)
def test_create_product_type_without_category_id_is_rejected(
    sut: ServiceUnderTest, name: str, fields: dict[str, str]
) -> None:
    """SPEC-PTY-20 · TC-PTY-20b"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_product_type(name, None)

    assert raised.value.fields == fields
    assert sut.commit.calls == 0


def test_create_product_type_accepts_a_category_id_written_as_digits(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-20 · TC-PTY-20c"""
    product_type = sut.service.create_product_type("Notebook", str(hardware.id))

    assert product_type.category is hardware


def test_update_product_type_renames_it_in_the_same_category(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-06 · TC-PTY-06a"""
    notebook = add_type(sut, "Notebook", hardware)

    updated = sut.service.update_product_type(notebook.id, name="Ultrabook")

    assert updated is notebook
    assert (notebook.name, notebook.category) == ("Ultrabook", hardware)
    assert sut.commit.calls == 1


def test_update_product_type_moves_it_to_another_category(
    sut: ServiceUnderTest, hardware: Category, office: Category
) -> None:
    """SPEC-PTY-06 · TC-PTY-06b"""
    notebook = add_type(sut, "Notebook", hardware)

    sut.service.update_product_type(notebook.id, category_id=office.id)

    assert notebook in office.product_types
    assert notebook not in hardware.product_types
    assert sut.commit.calls == 1


def test_update_product_type_to_its_own_name_in_other_case_is_allowed(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-06 · TC-PTY-06c"""
    notebook = add_type(sut, "Notebook", hardware)

    sut.service.update_product_type(notebook.id, name="NOTEBOOK")

    assert notebook.name == "NOTEBOOK"


def test_update_unknown_product_type_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-06 · TC-PTY-06d"""
    with pytest.raises(ProductTypeNotFoundError):
        sut.service.update_product_type(9999, name="X")

    assert sut.commit.calls == 0


@pytest.mark.parametrize(("name", "reason"), [("   ", "required"), (["x"], "invalid")])
def test_update_product_type_with_invalid_name_is_rejected(
    sut: ServiceUnderTest, hardware: Category, name: Any, reason: str
) -> None:
    """SPEC-PTY-15 · TC-PTY-15e"""
    notebook = add_type(sut, "Notebook", hardware)

    with pytest.raises(ValidationError) as raised:
        sut.service.update_product_type(notebook.id, name=name)

    assert raised.value.fields == {"name": reason}
    assert notebook.name == "Notebook"
    assert sut.commit.calls == 0


def test_update_product_type_to_unknown_category_is_rejected(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-16 · TC-PTY-16a"""
    notebook = add_type(sut, "Notebook", hardware)

    with pytest.raises(CategoryNotFoundError):
        sut.service.update_product_type(notebook.id, category_id=9999)

    assert notebook.category is hardware
    assert sut.commit.calls == 0


def test_moving_a_product_type_onto_a_taken_name_is_rejected(
    sut: ServiceUnderTest, hardware: Category, office: Category
) -> None:
    """SPEC-PTY-16 · TC-PTY-16b"""
    notebook = add_type(sut, "Notebook", hardware)
    add_type(sut, "notebook", office)

    with pytest.raises(DuplicateProductTypeError):
        sut.service.update_product_type(notebook.id, category_id=office.id)

    assert notebook.category is hardware
    assert sut.commit.calls == 0


def test_renaming_a_product_type_to_a_sibling_name_is_rejected(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-16 · TC-PTY-16c"""
    add_type(sut, "Notebook", hardware)
    desktop = add_type(sut, "Desktop", hardware)

    with pytest.raises(DuplicateProductTypeError):
        sut.service.update_product_type(desktop.id, name="NOTEBOOK")

    assert desktop.name == "Desktop"
    assert sut.commit.calls == 0


@pytest.mark.parametrize("category_id", [0, "abc", True])
def test_update_product_type_with_malformed_category_id_is_rejected(
    sut: ServiceUnderTest, hardware: Category, category_id: Any
) -> None:
    """SPEC-PTY-20 · TC-PTY-20d"""
    notebook = add_type(sut, "Notebook", hardware)

    with pytest.raises(ValidationError) as raised:
        sut.service.update_product_type(notebook.id, category_id=category_id)

    assert raised.value.fields == {"category_id": "invalid"}
    assert notebook.category is hardware
    assert sut.commit.calls == 0


def test_delete_product_type_removes_it_and_commits(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-07 · TC-PTY-07a"""
    notebook = add_type(sut, "Notebook", hardware)

    sut.service.delete_product_type(notebook.id)

    assert sut.product_types.get(notebook.id) is None
    assert sut.commit.calls == 1


def test_delete_unknown_product_type_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-07 · TC-PTY-07b"""
    with pytest.raises(ProductTypeNotFoundError):
        sut.service.delete_product_type(9999)

    assert sut.commit.calls == 0


def test_delete_product_type_with_an_inactive_product_is_rejected(
    sut: ServiceUnderTest, hardware: Category
) -> None:
    """SPEC-PTY-08 · TC-PTY-08a"""
    notebook = add_type(sut, "Notebook", hardware)
    Product(name="XPS 13", product_type=notebook, is_active=False)

    with pytest.raises(ProductTypeInUseError):
        sut.service.delete_product_type(notebook.id)

    assert sut.product_types.get(notebook.id) is notebook
    assert sut.commit.calls == 0


def group_names(groups: list[CategoryGroup]) -> list[tuple[str, list[str]]]:
    return [(g.category.name, [t.name for t in g.product_types]) for g in groups]


def test_list_product_types_groups_them_by_category_including_empty_ones(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-PTY-22 · TC-PTY-22a"""
    redes, audio, hardware = (Category(name=n) for n in ["Redes", "audio", "Hardware"])
    for category in (redes, audio, hardware):
        sut.categories.add(category)
    add_type(sut, "Router", redes)
    add_type(sut, "Access point", redes)
    add_type(sut, "Notebook", hardware)

    groups = sut.service.list_product_types()

    assert group_names(groups) == [
        ("audio", []),
        ("Hardware", ["Notebook"]),
        ("Redes", ["Access point", "Router"]),
    ]


def test_list_product_types_of_one_category_returns_only_its_group(
    sut: ServiceUnderTest, hardware: Category, office: Category
) -> None:
    """SPEC-PTY-10 · TC-PTY-10a"""
    add_type(sut, "Notebook", hardware)
    add_type(sut, "Silla", office)

    groups = sut.service.list_product_types(category_id=hardware.id)

    assert group_names(groups) == [("Hardware", ["Notebook"])]


def test_list_product_types_of_unknown_category_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PTY-18 · TC-PTY-18a"""
    with pytest.raises(CategoryNotFoundError):
        sut.service.list_product_types(category_id=9999)


@pytest.mark.parametrize("category_id", ["abc", "", "-1", "0", "1.5", "1" * 5000])
def test_list_product_types_with_malformed_category_id_is_rejected(
    sut: ServiceUnderTest, category_id: str
) -> None:
    """SPEC-PTY-20 · TC-PTY-20e"""
    with pytest.raises(ValidationError) as raised:
        sut.service.list_product_types(category_id=category_id)

    assert raised.value.fields == {"category_id": "invalid"}


@pytest.fixture
def reference_data(sut: ServiceUnderTest) -> Category:
    redes, audio, hardware, electronica = (
        Category(name=n) for n in ["Redes", "audio", "Hardware", "Electrónica"]
    )
    for category in (redes, audio, hardware, electronica):
        sut.categories.add(category)
    add_type(sut, "Router", redes)
    add_type(sut, "Access point", redes)
    add_type(sut, "Notebook", hardware)
    add_type(sut, "Ruteador USB", hardware)
    return hardware


def test_list_categories_with_q_keeps_only_names_containing_it(
    sut: ServiceUnderTest, reference_data: Category
) -> None:
    """SPEC-PTY-21 · TC-PTY-21a"""
    found = [c.name for c in sut.service.list_categories(q="RED")]
    none = sut.service.list_categories(q="zzz")

    assert found == ["Redes"]
    assert none == []


@pytest.mark.parametrize("q", ["", "   "])
def test_list_product_types_with_blank_q_ignores_it(
    sut: ServiceUnderTest, reference_data: Category, q: str
) -> None:
    """SPEC-PTY-22 · TC-PTY-22e"""
    groups = sut.service.list_product_types(q=q)

    assert group_names(groups) == group_names(sut.service.list_product_types())
    assert ("audio", []) in group_names(groups)


def test_list_product_types_with_q_groups_matches_and_omits_empty_categories(
    sut: ServiceUnderTest, reference_data: Category
) -> None:
    """SPEC-PTY-23 · TC-PTY-23a"""
    groups = sut.service.list_product_types(q="RUT")

    assert group_names(groups) == [("Hardware", ["Ruteador USB"]), ("Redes", ["Router"])]


def test_list_product_types_with_q_and_category_filters_inside_it(
    sut: ServiceUnderTest, reference_data: Category
) -> None:
    """SPEC-PTY-23 · TC-PTY-23d"""
    hardware = reference_data

    assert group_names(sut.service.list_product_types(category_id=hardware.id, q="note")) == [
        ("Hardware", ["Notebook"])
    ]
    assert sut.service.list_product_types(category_id=hardware.id, q="zzz") == []
    with pytest.raises(CategoryNotFoundError):
        sut.service.list_product_types(category_id=9999, q="a")
    with pytest.raises(ValidationError) as raised:
        sut.service.list_product_types(category_id="abc", q="a")
    assert raised.value.fields == {"category_id": "invalid"}


def test_list_product_types_q_does_not_match_category_names(
    sut: ServiceUnderTest, reference_data: Category
) -> None:
    """SPEC-PTY-23 · TC-PTY-23e"""
    assert sut.service.list_product_types(q="redes") == []
