"""Domain package: importing it registers every mapped class, listener and trigger DDL."""

from app.domain import milestone, products, state_change, ticket, users

__all__ = ["milestone", "products", "state_change", "ticket", "users"]
