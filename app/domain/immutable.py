"""Write barriers for records that must never change once saved."""

from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper

from app.domain.errors import ImmutableRecordError


def reject_update(mapper: Mapper[Any], connection: Connection, target: Any) -> None:
    raise ImmutableRecordError()


def reject_delete(mapper: Mapper[Any], connection: Connection, target: Any) -> None:
    raise ImmutableRecordError()


def make_immutable(model: type) -> type:
    """Make the ORM refuse to update or delete instances of the mapped class."""
    event.listen(model, "before_update", reject_update)
    event.listen(model, "before_delete", reject_delete)
    return model
