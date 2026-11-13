"""Paging value objects shared by the services and the repositories."""

from dataclasses import dataclass

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageRequest:
    """A requested window of a listing; pages are numbered from 1."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class Page[T]:
    """One page of results with the total of rows that match the filters."""

    items: list[T]
    page: int
    page_size: int
    total: int
