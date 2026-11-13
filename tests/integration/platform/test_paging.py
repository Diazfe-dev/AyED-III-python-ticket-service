from collections.abc import Iterator

import pytest
from sqlalchemy import Column, Integer, MetaData, Select, String, Table, event, insert, select
from sqlalchemy.orm import Session

from app.domain.paging import Page, PageRequest
from app.repositories.paging import fetch

metadata = MetaData()
entries = Table(
    "paging_entries",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("key", String, nullable=False),
    Column("active", Integer, nullable=False),
)


def _seed(session: Session, keys: list[str], active: list[int] | None = None) -> None:
    metadata.create_all(session.get_bind())
    flags = active or [1] * len(keys)
    session.execute(
        insert(entries),
        [{"key": key, "active": flag} for key, flag in zip(keys, flags, strict=True)],
    )
    session.commit()


def _ordered() -> Select:
    return select(entries.c.id).order_by(entries.c.key, entries.c.id)


@pytest.fixture
def executed(db_session: Session) -> Iterator[list[str]]:
    """The SQL statements the session's engine runs, in order."""
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        statements.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    yield statements
    event.remove(engine, "before_cursor_execute", record)


def test_fetch_with_window_returns_page_with_filtered_total(db_session: Session) -> None:
    """SPEC-PLT-17 · TC-PLT-17c"""
    _seed(db_session, ["a", "b", "c", "d", "e"], [1, 1, 0, 1, 1])
    statement = _ordered().where(entries.c.active == 1)

    result = fetch(db_session, statement, PageRequest(2, 3))

    assert isinstance(result, Page)
    assert (result.page, result.page_size, result.total) == (2, 3, 4)
    assert len(result.items) == 1


def test_fetch_without_window_returns_plain_list_in_statement_order(db_session: Session) -> None:
    """SPEC-PLT-18 · TC-PLT-18b"""
    _seed(db_session, ["e", "d", "c", "b", "a"])

    result = fetch(db_session, _ordered(), None)

    assert isinstance(result, list)
    assert result == [5, 4, 3, 2, 1]


def test_pages_with_tied_keys_neither_overlap_nor_skip(db_session: Session) -> None:
    """SPEC-PLT-21 · TC-PLT-21a"""
    _seed(db_session, ["a", "b", "c", "a", "b", "c", "a"])

    pages = [fetch(db_session, _ordered(), PageRequest(n, 3)) for n in (1, 2, 3)]
    joined = [item for page in pages for item in page.items]

    assert joined == fetch(db_session, _ordered(), None)
    assert len(joined) == 7


def test_page_beyond_the_last_is_empty_with_real_total(db_session: Session) -> None:
    """SPEC-PLT-22 · TC-PLT-22a"""
    _seed(db_session, ["a", "b", "c", "d", "e"])

    result = fetch(db_session, _ordered(), PageRequest(3, 5))

    assert result.items == []
    assert result.total == 5


def test_offset_that_does_not_fit_integer_skips_the_items_query(
    db_session: Session, executed: list[str]
) -> None:
    """SPEC-PLT-22 · TC-PLT-22b"""
    _seed(db_session, ["a", "b", "c", "d", "e"])
    executed.clear()

    result = fetch(db_session, _ordered(), PageRequest(page=10**18, page_size=100))

    assert result.items == []
    assert result.total == 5
    assert len(executed) == 1
    assert "count" in executed[0].lower()
