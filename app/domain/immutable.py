"""Write barriers for records that must never change once saved."""

from typing import Any

from sqlalchemy import DDL, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper

from app.domain.errors import ImmutableRecordError


def reject_update(mapper: Mapper[Any], connection: Connection, target: Any) -> None:
    raise ImmutableRecordError()


def reject_delete(mapper: Mapper[Any], connection: Connection, target: Any) -> None:
    raise ImmutableRecordError()


def _trigger(table: str, operation: str) -> DDL:
    name = f"{table}_no_{operation.lower()}"
    return DDL(
        f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {operation} ON {table} "
        f"BEGIN SELECT RAISE(ABORT, '{table} rows are immutable'); END"
    )


def make_immutable(model: type) -> type:
    """Make the ORM and the SQLite database refuse to update or delete the mapped class."""
    event.listen(model, "before_update", reject_update)
    event.listen(model, "before_delete", reject_delete)
    table = model.__table__
    for operation in ("UPDATE", "DELETE"):
        event.listen(
            table, "after_create", _trigger(table.name, operation).execute_if(dialect="sqlite")
        )
    return model
