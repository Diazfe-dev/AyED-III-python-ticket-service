import pytest
from flask import Flask
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.domain.errors import DuplicateProductTypeError, ProductTypeInUseError
from app.domain.products import Category, Product, ProductType
from app.repositories.product_type_repository import SqlAlchemyProductTypeRepository
from tests.conftest import MakeCategory, MakeProduct, MakeProductType
from tests.integration.catalog.queries import count_statements


def new_session(app: Flask) -> Session:
    return app.extensions[EXTENSION_KEY]["session_factory"]()


def test_added_product_type_keeps_its_category(
    app: Flask, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-03 · TC-PTY-03c"""
    hardware = make_category("Hardware")
    product_type = ProductType(name="Notebook", category=hardware)
    SqlAlchemyProductTypeRepository(db_session).add(product_type)
    db_session.commit()

    with new_session(app) as other_session:
        found = SqlAlchemyProductTypeRepository(other_session).get(product_type.id)

        assert found is not None
        assert found.category_id == hardware.id
        assert found.category.name == "Hardware"


def test_adding_a_duplicate_name_in_the_category_raises_domain_error(
    db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-05 · TC-PTY-05c"""
    hardware = make_category("Hardware")
    repository = SqlAlchemyProductTypeRepository(db_session)
    repository.add(ProductType(name="Notebook", category=hardware))

    with pytest.raises(DuplicateProductTypeError):
        repository.add(ProductType(name="notebook", category=hardware))


def test_find_by_name_in_category_only_looks_inside_that_category(
    db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-05 · TC-PTY-05d"""
    hardware, office = make_category("Hardware"), make_category("Oficina")
    repository = SqlAlchemyProductTypeRepository(db_session)
    in_hardware = ProductType(name="Notebook", category=hardware)
    repository.add(in_hardware)
    repository.add(ProductType(name="Notebook", category=office))
    db_session.commit()

    assert repository.find_by_name_in_category(" NOTEBOOK ", hardware.id) is in_hardware


def test_deleted_product_type_is_gone_and_its_category_stays(
    app: Flask, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-07 · TC-PTY-07c"""
    hardware = make_category("Hardware")
    repository = SqlAlchemyProductTypeRepository(db_session)
    product_type = ProductType(name="Notebook", category=hardware)
    repository.add(product_type)
    db_session.commit()

    repository.delete(product_type)
    db_session.commit()

    with new_session(app) as other_session:
        assert SqlAlchemyProductTypeRepository(other_session).get(product_type.id) is None
        assert other_session.get(Category, hardware.id) is not None


def test_get_with_an_id_beyond_sqlite_integers_finds_nothing(db_session: Session) -> None:
    """SPEC-PTY-06 · TC-PTY-06g"""
    assert SqlAlchemyProductTypeRepository(db_session).get(2**63) is None


def test_has_products_counts_inactive_products(
    db_session: Session,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-PTY-08 · TC-PTY-08d"""
    hardware = make_category("Hardware")
    used, empty = make_product_type(hardware), make_product_type(hardware)
    make_product(used, is_active=False)
    repository = SqlAlchemyProductTypeRepository(db_session)

    assert repository.has_products(used.id) is True
    assert repository.has_products(empty.id) is False


def test_deleting_a_product_type_with_products_raises_in_use_and_keeps_both_rows(
    app: Flask,
    db_session: Session,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
    make_product: MakeProduct,
) -> None:
    """SPEC-PTY-08 · TC-PTY-08b"""
    product_type = make_product_type(make_category("Hardware"))
    product = make_product(product_type)
    assert product_type.products == [product]

    with pytest.raises(ProductTypeInUseError) as raised:
        SqlAlchemyProductTypeRepository(db_session).delete(product_type)
    db_session.rollback()

    assert "FOREIGN KEY" in str(raised.value.__cause__)

    with new_session(app) as other_session:
        assert other_session.get(ProductType, product_type.id) is not None
        stored_product = other_session.get(Product, product.id)
        assert stored_product is not None
        assert stored_product.product_type_id == product_type.id


def test_search_matches_names_ignoring_case_in_category_and_name_order(
    db_session: Session, make_category: MakeCategory, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-23 · TC-PTY-23b"""
    hardware, redes, audio = (
        make_category("Hardware"),
        make_category("Redes"),
        make_category("audio"),
    )
    make_product_type(redes, "Router")
    make_product_type(hardware, "Router USB")
    make_product_type(audio, "Cámara")
    make_product_type(hardware, "Notebook")
    repository = SqlAlchemyProductTypeRepository(db_session)

    assert [t.name for t in repository.search("CÁM")] == ["Cámara"]
    assert [t.name for t in repository.search("rout")] == ["Router USB", "Router"]
    assert [t.name for t in repository.search("rout", category_id=redes.id)] == ["Router"]
    assert [t.name for t in repository.search("%")] == []


def test_search_loads_categories_without_extra_queries(
    db_session: Session, make_category: MakeCategory, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-23 · TC-PTY-23c"""
    for _ in range(3):
        category = make_category()
        make_product_type(category, "Uno")
        make_product_type(category, "Dos")
    db_session.expire_all()

    with count_statements(db_session) as statements:
        found = SqlAlchemyProductTypeRepository(db_session).search("o")
        names = [t.category.name for t in found]

    assert len(names) == 6
    assert len(statements) <= 2
