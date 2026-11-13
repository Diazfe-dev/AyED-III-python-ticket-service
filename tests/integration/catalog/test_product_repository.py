import pytest
from flask import Flask
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.domain.errors import DuplicateProductError
from app.domain.products import Category, Product, ProductType
from app.repositories.product_repository import SqlAlchemyProductRepository
from tests.conftest import MakeCategory, MakeProduct, MakeProductType
from tests.integration.catalog.queries import count_statements


def new_session(app: Flask) -> Session:
    return app.extensions[EXTENSION_KEY]["session_factory"]()


@pytest.fixture
def hardware(make_category: MakeCategory) -> Category:
    return make_category("Hardware")


@pytest.fixture
def notebook(hardware: Category, make_product_type: MakeProductType) -> ProductType:
    return make_product_type(hardware, "Notebook")


def test_added_product_is_active_by_default_and_keeps_its_type(
    app: Flask, db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-01 · TC-PRD-01b"""
    product = Product(name="XPS 13", product_type=notebook)
    SqlAlchemyProductRepository(db_session).add(product)
    db_session.commit()

    with new_session(app) as other_session:
        found = SqlAlchemyProductRepository(other_session).get(product.id)

        assert found is not None
        assert found.name == "XPS 13"
        assert found.product_type_id == notebook.id
        assert found.product_type.category.name == "Hardware"
        assert found.is_active is True


def test_product_repository_has_no_way_to_delete_products(db_session: Session) -> None:
    """SPEC-PRD-06 · TC-PRD-06b"""
    public = {name for name in dir(SqlAlchemyProductRepository) if not name.startswith("_")}

    assert not {name for name in public if "delete" in name or "remove" in name}


@pytest.fixture
def desktop(hardware: Category, make_product_type: MakeProductType) -> ProductType:
    return make_product_type(hardware, "Desktop")


def test_adding_a_duplicate_name_in_the_type_raises_domain_error(
    db_session: Session, notebook: ProductType
) -> None:
    """SPEC-PRD-13 · TC-PRD-13e"""
    repository = SqlAlchemyProductRepository(db_session)
    repository.add(Product(name="XPS 13", product_type=notebook))

    with pytest.raises(DuplicateProductError):
        repository.add(Product(name="xps 13", product_type=notebook))


def test_find_by_name_in_type_only_looks_inside_that_type(
    db_session: Session, notebook: ProductType, desktop: ProductType
) -> None:
    """SPEC-PRD-13 · TC-PRD-13f"""
    repository = SqlAlchemyProductRepository(db_session)
    in_notebook = Product(name="XPS 13", product_type=notebook)
    repository.add(in_notebook)
    repository.add(Product(name="XPS 13", product_type=desktop))
    db_session.commit()

    assert repository.find_by_name_in_type(" xps 13 ", notebook.id) is in_notebook
    assert repository.find_by_name_in_type("Otro", notebook.id) is None


def test_get_with_an_id_beyond_sqlite_integers_finds_nothing(db_session: Session) -> None:
    """SPEC-PRD-17 · TC-PRD-17c"""
    assert SqlAlchemyProductRepository(db_session).get(2**63) is None


@pytest.fixture
def catalog(
    make_category: MakeCategory, make_product_type: MakeProductType, make_product: MakeProduct
) -> dict[str, int]:
    """`xps 13` (Notebook), inactive `Optiplex` (Desktop) and `LaserJet` (Impresora, Oficina)."""
    hardware, office = make_category("Hardware"), make_category("Oficina")
    notebook = make_product_type(hardware, "Notebook")
    desktop = make_product_type(hardware, "Desktop")
    printer = make_product_type(office, "Impresora")
    make_product(notebook, "xps 13")
    make_product(desktop, "Optiplex", is_active=False)
    make_product(printer, "LaserJet")
    return {
        "hardware": hardware.id,
        "office": office.id,
        "notebook": notebook.id,
        "desktop": desktop.id,
    }


def names(products: list[Product]) -> list[str]:
    return [product.name for product in products]


def test_list_matching_exposes_type_category_and_state_of_every_product(
    db_session: Session, catalog: dict[str, int]
) -> None:
    """SPEC-PRD-07 · TC-PRD-07b"""
    db_session.expire_all()

    products = SqlAlchemyProductRepository(db_session).list_matching()

    described = {
        (p.name, p.product_type.name, p.product_type.category.name, p.is_active) for p in products
    }
    assert described == {
        ("xps 13", "Notebook", "Hardware", True),
        ("Optiplex", "Desktop", "Hardware", False),
        ("LaserJet", "Impresora", "Oficina", True),
    }


def test_list_matching_loads_types_and_categories_without_n_plus_one(
    db_session: Session,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-PRD-07 · TC-PRD-07c"""
    for category in [make_category(), make_category()]:
        make_product(make_product_type(category))
        make_product(make_product_type(category))
    third_type = make_product_type(category)
    make_product(third_type)
    make_product(third_type)
    db_session.expire_all()

    with count_statements(db_session) as statements:
        products = SqlAlchemyProductRepository(db_session).list_matching()
        described = [(p.product_type.name, p.product_type.category.name) for p in products]

    assert len(described) == 6
    assert len(statements) <= 3


def test_list_matching_orders_by_name_ignoring_case_then_by_id(
    db_session: Session, catalog: dict[str, int], make_product: MakeProduct
) -> None:
    """SPEC-PRD-21 · TC-PRD-21b"""
    desktop_xps = make_product(db_session.get(ProductType, catalog["desktop"]), "XPS 13")
    db_session.expire_all()

    products = SqlAlchemyProductRepository(db_session).list_matching()

    assert names(products) == ["LaserJet", "Optiplex", "xps 13", "XPS 13"]
    assert products[-1].id == desktop_xps.id


def test_list_matching_by_category_returns_products_of_its_types(
    db_session: Session, catalog: dict[str, int]
) -> None:
    """SPEC-PRD-08 · TC-PRD-08d"""
    products = SqlAlchemyProductRepository(db_session).list_matching(
        category_id=catalog["hardware"]
    )

    assert names(products) == ["Optiplex", "xps 13"]


def test_list_matching_by_product_type_returns_only_its_products(
    db_session: Session, catalog: dict[str, int]
) -> None:
    """SPEC-PRD-08 · TC-PRD-08e"""
    products = SqlAlchemyProductRepository(db_session).list_matching(
        product_type_id=catalog["notebook"]
    )

    assert names(products) == ["xps 13"]


def test_list_matching_by_category_and_type_returns_the_intersection(
    db_session: Session, catalog: dict[str, int]
) -> None:
    """SPEC-PRD-08 · TC-PRD-08f"""
    products = SqlAlchemyProductRepository(db_session).list_matching(
        category_id=catalog["hardware"], product_type_id=catalog["notebook"]
    )

    assert names(products) == ["xps 13"]


def test_list_matching_with_a_type_outside_the_category_is_empty(
    db_session: Session, catalog: dict[str, int]
) -> None:
    """SPEC-PRD-20 · TC-PRD-20b"""
    products = SqlAlchemyProductRepository(db_session).list_matching(
        category_id=catalog["office"], product_type_id=catalog["notebook"]
    )

    assert products == []


def test_list_matching_is_active_true_skips_inactive_products(
    db_session: Session, catalog: dict[str, int]
) -> None:
    """SPEC-PRD-10 · TC-PRD-10b"""
    products = SqlAlchemyProductRepository(db_session).list_matching(is_active=True)

    assert names(products) == ["LaserJet", "xps 13"]


def test_list_matching_is_active_is_a_tri_state_filter(
    db_session: Session, catalog: dict[str, int]
) -> None:
    """SPEC-PRD-27 · TC-PRD-27b"""
    repository = SqlAlchemyProductRepository(db_session)

    assert names(repository.list_matching(is_active=False)) == ["Optiplex"]
    assert names(repository.list_matching(is_active=True)) == ["LaserJet", "xps 13"]
    assert names(repository.list_matching()) == ["LaserJet", "Optiplex", "xps 13"]


def test_get_many_returns_active_and_inactive_products_ordered_by_id(
    db_session: Session, notebook: ProductType, make_product: MakeProduct
) -> None:
    """SPEC-TKT-08 · TC-TKT-08a"""
    xps = make_product(notebook, "XPS 13")
    optiplex = make_product(notebook, "Optiplex", is_active=False)
    wanted = [optiplex.id, xps.id, 9999]
    db_session.expire_all()

    with count_statements(db_session) as statements:
        products = SqlAlchemyProductRepository(db_session).get_many(wanted)
        described = [(p.name, p.product_type.name, p.product_type.category.name) for p in products]

    assert described == [("XPS 13", "Notebook", "Hardware"), ("Optiplex", "Notebook", "Hardware")]
    assert len(statements) <= 3


def test_get_many_ignores_ids_beyond_sqlite_integers(
    db_session: Session, notebook: ProductType, make_product: MakeProduct
) -> None:
    """SPEC-TKT-08 · TC-TKT-08b"""
    xps = make_product(notebook, "XPS 13")

    products = SqlAlchemyProductRepository(db_session).get_many(
        [xps.id, 2**63, 99999999999999999999]
    )

    assert names(products) == ["XPS 13"]


def test_get_many_skips_duplicates_and_does_not_query_an_empty_list(
    db_session: Session, notebook: ProductType, make_product: MakeProduct
) -> None:
    """SPEC-TKT-08 · TC-TKT-08c"""
    xps = make_product(notebook, "XPS 13")
    repository = SqlAlchemyProductRepository(db_session)

    assert names(repository.get_many([xps.id, xps.id])) == ["XPS 13"]
    with count_statements(db_session) as statements:
        assert repository.get_many([]) == []
        assert repository.get_many([2**63]) == []

    assert statements == []
