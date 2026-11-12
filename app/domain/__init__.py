"""Domain package: importing it registers every mapped class, listener and trigger DDL."""

from app.domain import milestone, notifications, products, state_change, ticket, users

__all__ = ["milestone", "notifications", "products", "state_change", "ticket", "users"]
