from dataclasses import dataclass
from typing import Any

import pytest

from app.domain.errors import (
    DuplicateProductError,
    PermissionDeniedError,
    ProductNotFoundError,
    ProductTypeNotFoundError,
    ValidationError,
)
from app.domain.paging import Page
from app.domain.products import Product, ProductType
from app.domain.users import Admin, Client, Representative
from app.services.product_service import ProductService
from tests.unit.catalog.fakes import (
    FakeProductRepository,
    FakeProductTypeRepository,
)
from tests.unit.fakes import CommitSpy


@dataclass
class ServiceUnderTest:
    service: ProductService
    products: FakeProductRepository
    product_types: FakeProductTypeRepository
    commit: CommitSpy
    notebook: ProductType
    desktop: ProductType
    printer: ProductType

    def add_product(self, name: str, product_type: ProductType, is_active: bool = True) -> Product:
        product = Product(name=name, product_type=product_type, is_active=is_active)
        self.products.add(product)
        return product


@pytest.fixture
def sut() -> ServiceUnderTest:
    """`Notebook` (id 1), `Desktop` and `Impresora`."""
    products, product_types = FakeProductRepository(), FakeProductTypeRepository()
    commit = CommitSpy()
    notebook = ProductType(name="Notebook")
    desktop = ProductType(name="Desktop")
    printer = ProductType(name="Impresora")
    for product_type in (notebook, desktop, printer):
        product_types.add(product_type)
    service = ProductService(products, product_types, commit)
    return ServiceUnderTest(
        service,
        products,
        product_types,
        commit,
        notebook,
        desktop,
        printer,
    )


def test_create_product_stores_an_active_product_of_the_type(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-01 · TC-PRD-01c"""
    product = sut.service.create_product("XPS 13", sut.notebook.id)

    assert product.name == "XPS 13"
    assert product.product_type is sut.notebook
    assert product.is_active is True
    assert sut.products.get(product.id) is product
    assert sut.commit.calls == 1


def assert_nothing_created(sut: ServiceUnderTest) -> None:
    assert sut.products.products == {}
    assert sut.commit.calls == 0


@pytest.mark.parametrize("name", [None, "", "   "])
def test_create_product_without_name_is_rejected(sut: ServiceUnderTest, name: Any) -> None:
    """SPEC-PRD-03 · TC-PRD-03a"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_product(name, sut.notebook.id)

    assert raised.value.fields == {"name": "required"}
    assert_nothing_created(sut)


@pytest.mark.parametrize("name", [123, ["XPS"], {"name": "x"}])
def test_create_product_with_non_text_name_is_rejected(sut: ServiceUnderTest, name: Any) -> None:
    """SPEC-PRD-11 · TC-PRD-11a"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_product(name, sut.notebook.id)

    assert raised.value.fields == {"name": "invalid"}
    assert_nothing_created(sut)


@pytest.mark.parametrize(
    "product_type_id", [True, False, 1.5, 0, -3, "abc", "-1", "0", "1.5", "", [1]]
)
def test_create_product_with_malformed_product_type_id_is_rejected(
    sut: ServiceUnderTest, product_type_id: Any
) -> None:
    """SPEC-PRD-33 · TC-PRD-33a"""
    assert sut.notebook.id == 1

    with pytest.raises(ValidationError) as raised:
        sut.service.create_product("XPS 13", product_type_id)

    assert raised.value.fields == {"product_type_id": "invalid"}
    assert_nothing_created(sut)


@pytest.mark.parametrize(
    ("name", "fields"),
    [
        ("XPS 13", {"product_type_id": "required"}),
        ("", {"name": "required", "product_type_id": "required"}),
    ],
)
def test_create_product_without_product_type_id_is_rejected_with_the_name(
    sut: ServiceUnderTest, name: str, fields: dict[str, str]
) -> None:
    """SPEC-PRD-33 · TC-PRD-33b"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_product(name, None)

    assert raised.value.fields == fields
    assert_nothing_created(sut)


def test_create_product_accepts_a_product_type_id_written_with_digits(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-PRD-33 · TC-PRD-33c"""
    product = sut.service.create_product("XPS 13", "1")

    assert product.product_type is sut.notebook


def test_create_product_of_unknown_type_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-02 · TC-PRD-02a"""
    with pytest.raises(ProductTypeNotFoundError):
        sut.service.create_product("XPS 13", 9999)

    assert_nothing_created(sut)


def test_create_product_with_a_taken_name_in_the_type_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-13 · TC-PRD-13a"""
    existing = sut.add_product("XPS 13", sut.notebook)

    with pytest.raises(DuplicateProductError):
        sut.service.create_product(" xps 13 ", sut.notebook.id)

    assert list(sut.products.products.values()) == [existing]
    assert sut.commit.calls == 0


def test_create_product_allows_a_name_taken_in_another_type(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-13 · TC-PRD-13b"""
    sut.add_product("XPS 13", sut.notebook)

    product = sut.service.create_product("XPS 13", sut.desktop.id)

    assert product.product_type is sut.desktop
    assert sut.commit.calls == 1


def test_update_product_renames_it_and_keeps_its_type(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-04 · TC-PRD-04a"""
    product = sut.add_product("XPS 13", sut.notebook)

    sut.service.update_product(product.id, name="XPS 15")

    assert product.name == "XPS 15"
    assert product.product_type is sut.notebook
    assert sut.commit.calls == 1


def test_update_product_moves_it_to_another_type(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-04 · TC-PRD-04b"""
    product = sut.add_product("XPS 13", sut.notebook)

    sut.service.update_product(product.id, product_type_id=sut.desktop.id)

    assert product in sut.desktop.products
    assert product not in sut.notebook.products
    assert sut.commit.calls == 1


def test_update_product_to_its_own_name_in_other_case_is_allowed(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-04 · TC-PRD-04c"""
    product = sut.add_product("XPS 13", sut.notebook)

    sut.service.update_product(product.id, name="xps 13")

    assert product.name == "xps 13"


def test_update_unknown_product_is_not_found(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-17 · TC-PRD-17a"""
    with pytest.raises(ProductNotFoundError):
        sut.service.update_product(9999, name="X")

    assert sut.commit.calls == 0


def test_update_inactive_product_keeps_it_inactive(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-19 · TC-PRD-19a"""
    product = sut.add_product("XPS 13", sut.notebook, is_active=False)

    sut.service.update_product(product.id, name="XPS 15")

    assert product.name == "XPS 15"
    assert product.is_active is False
    assert sut.commit.calls == 1


@pytest.mark.parametrize(("name", "reason"), [("   ", "required"), (5, "invalid")])
def test_update_product_with_invalid_name_is_rejected(
    sut: ServiceUnderTest, name: Any, reason: str
) -> None:
    """SPEC-PRD-11 · TC-PRD-11b"""
    product = sut.add_product("XPS 13", sut.notebook)

    with pytest.raises(ValidationError) as raised:
        sut.service.update_product(product.id, name=name)

    assert raised.value.fields == {"name": reason}
    assert product.name == "XPS 13"
    assert sut.commit.calls == 0


def test_update_product_to_unknown_type_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-12 · TC-PRD-12a"""
    product = sut.add_product("XPS 13", sut.notebook)

    with pytest.raises(ProductTypeNotFoundError):
        sut.service.update_product(product.id, product_type_id=9999)

    assert product.product_type is sut.notebook
    assert sut.commit.calls == 0


def test_move_product_onto_a_taken_name_is_rejected(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-13 · TC-PRD-13c"""
    sut.add_product("XPS 13", sut.notebook)
    desktop_xps = sut.add_product("xps 13", sut.desktop)

    with pytest.raises(DuplicateProductError):
        sut.service.update_product(desktop_xps.id, product_type_id=sut.notebook.id)

    assert desktop_xps.product_type is sut.desktop
    assert sut.commit.calls == 0


def test_rename_product_to_the_name_of_an_inactive_sibling_is_rejected(
    sut: ServiceUnderTest,
) -> None:
    """SPEC-PRD-13 · TC-PRD-13d"""
    sut.add_product("XPS 13", sut.notebook, is_active=False)
    xps15 = sut.add_product("XPS 15", sut.notebook)

    with pytest.raises(DuplicateProductError):
        sut.service.update_product(xps15.id, name="XPS 13")

    assert xps15.name == "XPS 15"
    assert sut.commit.calls == 0


@pytest.mark.parametrize("product_type_id", [0, "abc", True])
def test_update_product_with_malformed_product_type_id_is_rejected(
    sut: ServiceUnderTest, product_type_id: Any
) -> None:
    """SPEC-PRD-33 · TC-PRD-33d"""
    product = sut.add_product("XPS 13", sut.notebook)

    with pytest.raises(ValidationError) as raised:
        sut.service.update_product(product.id, product_type_id=product_type_id)

    assert raised.value.fields == {"product_type_id": "invalid"}
    assert product.product_type is sut.notebook
    assert sut.commit.calls == 0


def test_deactivate_product_keeps_it_inactive_and_commits(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-05 · TC-PRD-05b"""
    product = sut.add_product("XPS 13", sut.notebook)

    deactivated = sut.service.deactivate_product(product.id)

    assert deactivated is product
    assert product.is_active is False
    assert sut.products.get(product.id) is product
    assert sut.commit.calls == 1


def test_deactivate_unknown_product_is_not_found(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-17 · TC-PRD-17b"""
    with pytest.raises(ProductNotFoundError):
        sut.service.deactivate_product(9999)

    assert sut.commit.calls == 0


def test_deactivate_an_inactive_product_succeeds_without_changes(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-18 · TC-PRD-18a"""
    product = sut.add_product("XPS 13", sut.notebook, is_active=False)

    deactivated = sut.service.deactivate_product(product.id)

    assert deactivated is product
    assert product.is_active is False


def test_activate_product_reactivates_it_and_commits(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-22 · TC-PRD-22b"""
    product = sut.add_product("Optiplex", sut.desktop, is_active=False)

    activated = sut.service.activate_product(product.id)

    assert activated is product
    assert product.is_active is True
    assert sut.commit.calls == 1


def test_activate_an_active_product_is_idempotent(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-23 · TC-PRD-23a"""
    product = sut.add_product("XPS 13", sut.notebook)

    activated = sut.service.activate_product(product.id)

    assert activated is product
    assert product.is_active is True
    assert sut.commit.calls == 1


def test_activate_unknown_product_is_not_found(sut: ServiceUnderTest) -> None:
    """SPEC-PRD-24 · TC-PRD-24a"""
    with pytest.raises(ProductNotFoundError):
        sut.service.activate_product(9999)

    assert sut.commit.calls == 0


@pytest.fixture
def listed(sut: ServiceUnderTest) -> ServiceUnderTest:
    """`xps 13` (Notebook), inactive `Optiplex` (Desktop) and `LaserJet` (Impresora)."""
    sut.add_product("xps 13", sut.notebook)
    sut.add_product("Optiplex", sut.desktop, is_active=False)
    sut.add_product("LaserJet", sut.printer)
    return sut


def names(products: list[Product]) -> list[str]:
    return [product.name for product in products]


def test_list_products_returns_every_product_including_inactive(listed: ServiceUnderTest) -> None:
    """SPEC-PRD-31 · TC-PRD-31a"""
    assert set(names(listed.service.list_products())) == {"xps 13", "Optiplex", "LaserJet"}


def test_list_products_by_product_type(listed: ServiceUnderTest) -> None:
    """SPEC-PRD-32 · TC-PRD-32a"""
    products = listed.service.list_products(product_type_id=listed.notebook.id)

    assert names(products) == ["xps 13"]


def test_product_listings_are_ordered_alphabetically_ignoring_case(
    listed: ServiceUnderTest,
) -> None:
    """SPEC-PRD-21 · TC-PRD-21a"""
    assert names(listed.service.list_products()) == ["LaserJet", "Optiplex", "xps 13"]
    assert names(listed.service.list_available_products()) == ["LaserJet", "xps 13"]


MALFORMED_FILTERS = ["abc", "", "-1", "0", "1.5", "9" * 5000]


@pytest.mark.parametrize("value", MALFORMED_FILTERS)
def test_list_products_with_a_malformed_type_filter_is_rejected(
    listed: ServiceUnderTest, value: str
) -> None:
    """SPEC-PRD-33 · TC-PRD-33e"""
    with pytest.raises(ValidationError) as raised:
        listed.service.list_products(product_type_id=value)

    assert raised.value.fields == {"product_type_id": "invalid"}


def test_list_products_of_unknown_product_type_is_not_found(listed: ServiceUnderTest) -> None:
    """SPEC-PRD-34 · TC-PRD-34a"""
    with pytest.raises(ProductTypeNotFoundError):
        listed.service.list_products(product_type_id=9999)


def test_available_products_are_only_the_active_ones(listed: ServiceUnderTest) -> None:
    """SPEC-PRD-10 · TC-PRD-10a"""
    assert names(listed.service.list_available_products()) == ["LaserJet", "xps 13"]


@pytest.fixture
def searchable(listed: ServiceUnderTest) -> ServiceUnderTest:
    """The `listed` data plus `XPS 15` (Notebook), `Cámara IP` and `50% Toner` (Impresora)."""
    listed.add_product("XPS 15", listed.notebook)
    listed.add_product("Cámara IP", listed.printer)
    listed.add_product("50% Toner", listed.printer)
    return listed


def test_list_products_filters_by_search_text_alone_and_with_other_filters(
    searchable: ServiceUnderTest,
) -> None:
    """SPEC-PRD-26 · TC-PRD-26a"""
    service = searchable.service

    assert names(service.list_products(q="XPS")) == ["xps 13", "XPS 15"]
    combined = service.list_products(
        q="xps", product_type_id=searchable.notebook.id, is_active="true"
    )
    assert names(combined) == ["xps 13", "XPS 15"]


def test_list_products_ignores_a_blank_search_text(searchable: ServiceUnderTest) -> None:
    """SPEC-PRD-26 · TC-PRD-26a"""
    everything = names(searchable.service.list_products())

    assert names(searchable.service.list_products(q="   ")) == everything
    assert names(searchable.service.list_products(q="")) == everything


def test_list_products_filters_by_state(searchable: ServiceUnderTest) -> None:
    """SPEC-PRD-27 · TC-PRD-27a"""
    service = searchable.service

    assert names(service.list_products(is_active="false")) == ["Optiplex"]
    active_notebooks = service.list_products(
        is_active="true", product_type_id=searchable.notebook.id
    )
    assert names(active_notebooks) == ["xps 13", "XPS 15"]


@pytest.mark.parametrize("value", ["", "yes", "True", "0"])
def test_list_products_with_a_malformed_state_is_rejected(
    searchable: ServiceUnderTest, value: str
) -> None:
    """SPEC-PRD-28 · TC-PRD-28a"""
    with pytest.raises(ValidationError) as raised:
        searchable.service.list_products(is_active=value)

    assert raised.value.fields == {"is_active": "invalid"}


def test_list_products_reports_a_malformed_state_with_a_malformed_filter(
    searchable: ServiceUnderTest,
) -> None:
    """SPEC-PRD-28 · TC-PRD-28a"""
    with pytest.raises(ValidationError) as raised:
        searchable.service.list_products(is_active="yes", product_type_id="abc")

    assert raised.value.fields == {"is_active": "invalid", "product_type_id": "invalid"}


def test_list_products_validates_the_query_before_looking_up_the_type(
    searchable: ServiceUnderTest,
) -> None:
    """SPEC-PRD-28 · TC-PRD-28a"""
    with pytest.raises(ValidationError) as raised:
        searchable.service.list_products(product_type_id=9999, is_active="yes")

    assert raised.value.fields == {"is_active": "invalid"}


def test_list_products_returns_the_page_asked_for(searchable: ServiceUnderTest) -> None:
    """SPEC-PRD-29 · TC-PRD-29a"""
    page = searchable.service.list_products(page="1", page_size="2")

    assert isinstance(page, Page)
    assert names(page.items) == ["50% Toner", "Cámara IP"]
    assert (page.page, page.page_size, page.total) == (1, 2, 6)


def test_list_products_reports_bad_pagination_together_with_the_filters(
    searchable: ServiceUnderTest,
) -> None:
    """SPEC-PRD-29 · TC-PRD-29b"""
    with pytest.raises(ValidationError) as raised:
        searchable.service.list_products(page="0", product_type_id="x")
    assert raised.value.fields == {"page": "invalid", "product_type_id": "invalid"}

    with pytest.raises(ValidationError) as raised:
        searchable.service.list_products(page_size="101")
    assert raised.value.fields == {"page_size": "invalid"}

    with pytest.raises(ValidationError) as raised:
        searchable.service.list_products(product_type_id=9999, page="0")
    assert raised.value.fields == {"page": "invalid"}


def test_available_products_are_searched_by_text(searchable: ServiceUnderTest) -> None:
    """SPEC-PRD-26 · TC-PRD-26d"""
    assert names(searchable.service.list_available_products(q="o")) == ["50% Toner"]


def test_available_products_ignore_a_blank_search_text(searchable: ServiceUnderTest) -> None:
    """SPEC-PRD-26 · TC-PRD-26d"""
    everything = names(searchable.service.list_available_products())

    assert names(searchable.service.list_available_products(q="  ")) == everything


def test_available_products_are_paged(searchable: ServiceUnderTest) -> None:
    """SPEC-PRD-29 · TC-PRD-29c"""
    page = searchable.service.list_available_products(page_size="2")

    assert isinstance(page, Page)
    assert (page.page, page.page_size, page.total) == (1, 2, 5)
    assert names(page.items) == ["50% Toner", "Cámara IP"]


@pytest.mark.parametrize(
    ("page", "page_size", "field"), [("0", None, "page"), (None, "101", "page_size")]
)
def test_available_products_with_bad_pagination_are_rejected(
    searchable: ServiceUnderTest, page: str | None, page_size: str | None, field: str
) -> None:
    """SPEC-PRD-29 · TC-PRD-29c"""
    with pytest.raises(ValidationError) as raised:
        searchable.service.list_available_products(page=page, page_size=page_size)

    assert raised.value.fields == {field: "invalid"}


@pytest.fixture
def admin() -> Admin:
    return Admin(name="Root", email="root@x.com", password_hash="x")


@pytest.fixture
def rosa() -> Representative:
    return Representative(name="Rosa", email="rosa@x.com", password_hash="x")


@pytest.fixture
def ana() -> Client:
    return Client(name="Ana", email="ana@x.com", password_hash="x")


def test_admin_keeps_creating_products(sut: ServiceUnderTest, admin: Admin) -> None:
    """SPEC-PRD-01 · TC-PRD-01e"""
    product = sut.service.create_product("XPS 15", sut.notebook.id, actor=admin)

    assert product.is_active is True
    assert sut.products.get(product.id) is product
    assert sut.commit.calls == 1


def test_representative_creates_an_active_product(
    sut: ServiceUnderTest, rosa: Representative
) -> None:
    """SPEC-PRD-35 · TC-PRD-35a"""
    product = sut.service.create_product("XPS 15", sut.notebook.id, actor=rosa)

    assert product.is_active is True
    assert product.product_type is sut.notebook
    assert sut.products.get(product.id) is product
    assert sut.commit.calls == 1


def test_representative_gets_the_same_rules_as_the_admin(
    sut: ServiceUnderTest, rosa: Representative
) -> None:
    """SPEC-PRD-35 · TC-PRD-35b"""
    sut.add_product("xps 13", sut.notebook)
    sut.commit.calls = 0

    with pytest.raises(ValidationError) as blank:
        sut.service.create_product("   ", sut.notebook.id, actor=rosa)
    with pytest.raises(ValidationError) as malformed:
        sut.service.create_product("XPS 15", "abc", actor=rosa)
    with pytest.raises(ProductTypeNotFoundError):
        sut.service.create_product("XPS 15", 9999, actor=rosa)
    with pytest.raises(DuplicateProductError):
        sut.service.create_product(" xps 13 ", sut.notebook.id, actor=rosa)

    assert blank.value.fields == {"name": "required"}
    assert malformed.value.fields == {"product_type_id": "invalid"}
    assert [product.name for product in sut.products.products.values()] == ["xps 13"]
    assert sut.commit.calls == 0


def test_client_cannot_create_products(sut: ServiceUnderTest, ana: Client) -> None:
    """SPEC-PRD-37 · TC-PRD-37a"""
    with pytest.raises(PermissionDeniedError):
        sut.service.create_product("XPS 15", sut.notebook.id, actor=ana)

    assert_nothing_created(sut)


def test_the_format_is_checked_before_the_role(sut: ServiceUnderTest, ana: Client) -> None:
    """SPEC-PRD-37 · TC-PRD-37b"""
    with pytest.raises(ValidationError) as raised:
        sut.service.create_product("", "abc", actor=ana)

    assert raised.value.fields == {"name": "required", "product_type_id": "invalid"}


def test_the_role_is_checked_before_the_type_lookup(sut: ServiceUnderTest, ana: Client) -> None:
    """SPEC-PRD-37 · TC-PRD-37c"""
    with pytest.raises(PermissionDeniedError):
        sut.service.create_product("XPS 15", 9999, actor=ana)
