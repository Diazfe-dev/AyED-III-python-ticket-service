"""Declarative base shared by every mapped entity."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
