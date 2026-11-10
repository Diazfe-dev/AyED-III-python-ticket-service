import pytest
from flask import Flask
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import EXTENSION_KEY
from app.domain.errors import CategoryInUseError, DuplicateCategoryError
from app.domain.products import Category, ProductType
from app.repositories.category_repository import SqlAlchemyCategoryRepository
from tests.conftest import MakeCategory, MakeProductType
from tests.integration.catalog.queries import count_statements


def test_added_category_can_be_read_from_another_session(app: Flask, db_session: Session) -> None:
    """SPEC-PTY-01 · TC-PTY-01b"""
    category = Category(name="Hardware")
    SqlAlchemyCategoryRepository(db_session).add(category)
    db_session.commit()

    with app.extensions[EXTENSION_KEY]["session_factory"]() as other_session:
        found = SqlAlchemyCategoryRepository(other_session).get(category.id)

        assert found is not None
        assert found.name == "Hardware"


def test_unique_key_compares_non_ascii_names_without_case(db_session: Session) -> None:
    """SPEC-PTY-02 · TC-PTY-02e"""
    repository = SqlAlchemyCategoryRepository(db_session)
    audio = Category(name="áudio")
    repository.add(audio)
    db_session.commit()

    with pytest.raises(DuplicateCategoryError):
        repository.add(Category(name="ÁUDIO"))
    db_session.rollback()

    assert repository.find_by_name("ÁUDIO") is audio


def test_adding_a_duplicate_name_raises_domain_error(db_session: Session) -> None:
    """SPEC-PTY-02 · TC-PTY-02f"""
    repository = SqlAlchemyCategoryRepository(db_session)
    repository.add(Category(name="Audio"))

    with pytest.raises(DuplicateCategoryError):
        repository.add(Category(name="AUDIO"))


def test_find_by_name_uses_the_normalized_key(db_session: Session) -> None:
    """SPEC-PTY-02 · TC-PTY-02g"""
    repository = SqlAlchemyCategoryRepository(db_session)
    hardware = Category(name="Hardware")
    repository.add(hardware)
    db_session.commit()

    assert repository.find_by_name(" hardware ") is hardware
    assert repository.find_by_name("Redes") is None


def test_list_all_orders_categories_by_name_ignoring_case(db_session: Session) -> None:
    """SPEC-PTY-17 · TC-PTY-17a"""
    repository = SqlAlchemyCategoryRepository(db_session)
    for name in ["redes", "Audio", "hardware"]:
        repository.add(Category(name=name))
    db_session.commit()

    assert [category.name for category in repository.list_all()] == ["Audio", "hardware", "redes"]


def new_session(app: Flask) -> Session:
    return app.extensions[EXTENSION_KEY]["session_factory"]()


def test_deleted_category_is_gone_for_another_session(
    app: Flask, db_session: Session, make_category: MakeCategory
) -> None:
    """SPEC-PTY-13 · TC-PTY-13c"""
    category = make_category()
    SqlAlchemyCategoryRepository(db_session).delete(category)
    db_session.commit()

    with new_session(app) as other_session:
        assert SqlAlchemyCategoryRepository(other_session).get(category.id) is None


def test_has_product_types_tells_whether_a_category_is_in_use(
    db_session: Session, make_category: MakeCategory, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-14 · TC-PTY-14b"""
    used, empty = make_category(), make_category()
    make_product_type(used)
    repository = SqlAlchemyCategoryRepository(db_session)

    assert repository.has_product_types(used.id) is True
    assert repository.has_product_types(empty.id) is False


def test_deleting_a_category_with_types_raises_in_use_and_keeps_both_rows(
    app: Flask,
    db_session: Session,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
) -> None:
    """SPEC-PTY-14 · TC-PTY-14c"""
    category = make_category()
    product_type = make_product_type(category)
    assert category.product_types == [product_type]

    with pytest.raises(CategoryInUseError) as raised:
        SqlAlchemyCategoryRepository(db_session).delete(category)
    db_session.rollback()

    assert "FOREIGN KEY" in str(raised.value.__cause__)

    with new_session(app) as other_session:
        assert other_session.get(Category, category.id) is not None
        stored_type = other_session.get(ProductType, product_type.id)
        assert stored_type is not None
        assert stored_type.category_id == category.id


def test_foreign_key_rejects_deleting_a_category_with_raw_sql(
    db_session: Session, make_category: MakeCategory, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-14 · TC-PTY-14d"""
    category = make_category()
    make_product_type(category)

    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM categories WHERE id = :id"), {"id": category.id})


@pytest.fixture
def grouped_catalog(make_category: MakeCategory, make_product_type: MakeProductType) -> None:
    """`Redes` with two types, `audio` without types and `Hardware` with one type."""
    redes = make_category("Redes")
    make_category("audio")
    hardware = make_category("Hardware")
    make_product_type(redes, "Router")
    make_product_type(redes, "Access point")
    make_product_type(hardware, "Notebook")


def names_by_group(categories: list[Category]) -> list[tuple[str, list[str]]]:
    return [(c.name, [t.name for t in c.product_types]) for c in categories]


@pytest.mark.usefixtures("grouped_catalog")
def test_list_with_product_types_orders_groups_and_types_by_name(db_session: Session) -> None:
    """SPEC-PTY-09 · TC-PTY-09b"""
    db_session.expire_all()

    categories = SqlAlchemyCategoryRepository(db_session).list_with_product_types()

    assert names_by_group(categories) == [
        ("audio", []),
        ("Hardware", ["Notebook"]),
        ("Redes", ["Access point", "Router"]),
    ]


def test_list_with_product_types_loads_everything_in_two_queries(
    db_session: Session, make_category: MakeCategory, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-09 · TC-PTY-09c"""
    for _ in range(3):
        category = make_category()
        make_product_type(category)
        make_product_type(category)
    db_session.expire_all()

    with count_statements(db_session) as statements:
        categories = SqlAlchemyCategoryRepository(db_session).list_with_product_types()
        names = [t.name for category in categories for t in category.product_types]

    assert len(names) == 6
    assert len(statements) <= 2


def test_get_with_an_id_beyond_sqlite_integers_finds_nothing(db_session: Session) -> None:
    """SPEC-PTY-18 · TC-PTY-18d"""
    assert SqlAlchemyCategoryRepository(db_session).get(2**63) is None
