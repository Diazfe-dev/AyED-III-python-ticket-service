"""Runs a listing statement, whole or one page at a time."""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db import fits_integer_column
from app.domain.paging import Page, PageRequest


def fetch(
    session: Session, statement: Select[Any], window: PageRequest | None
) -> list[Any] | Page[Any]:
    """The rows of `statement`, or the page `window` asks for with the total of matching rows.

    The statement carries its own order, ending in the id; `fetch` never orders.
    """
    if window is None:
        return list(session.scalars(statement).all())
    counted = select(func.count()).select_from(statement.order_by(None).subquery())
    total = session.scalar(counted) or 0
    items: list[Any] = []
    if fits_integer_column(window.offset):
        items = list(session.scalars(statement.limit(window.limit).offset(window.offset)).all())
    return Page(items=items, page=window.page, page_size=window.page_size, total=total)
