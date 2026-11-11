"""JSON input and output shared by the controllers."""

from typing import Any

from flask import request

from app.domain.products import Category, Product, ProductType
from app.domain.ticket import Ticket
from app.domain.users import User


def json_body() -> dict[str, Any]:
    """The request JSON object, or an empty one when the body is missing or not an object."""
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def session_user_json(user: User) -> dict[str, Any]:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


def user_json(user: User) -> dict[str, Any]:
    """Public representation of a user; it never includes the password hash."""
    return session_user_json(user) | {
        "preferred_channel": user.preferred_channel,
        "is_active": user.is_active,
    }


def category_json(category: Category) -> dict[str, Any]:
    return {"id": category.id, "name": category.name}


def product_type_json(product_type: ProductType) -> dict[str, Any]:
    return {
        "id": product_type.id,
        "name": product_type.name,
        "category_id": product_type.category_id,
    }


def category_group_json(category: Category) -> dict[str, Any]:
    """A category with its product types, already ordered by name."""
    return category_json(category) | {
        "product_types": [product_type_json(t) for t in category.product_types]
    }


def product_json(product: Product) -> dict[str, Any]:
    """A product with its type and the category of that type."""
    return {
        "id": product.id,
        "name": product.name,
        "is_active": product.is_active,
        "product_type": product_type_json(product.product_type),
        "category": category_json(product.product_type.category),
    }


def party_json(user: User) -> dict[str, Any]:
    """The part of a ticket participant that the other participant may see."""
    return {"id": user.id, "name": user.name}


def ticket_json(ticket: Ticket) -> dict[str, Any]:
    return {
        "id": ticket.id,
        "state": ticket.state_name,
        "client": party_json(ticket.client),
        "representative": party_json(ticket.representative),
        "products": [product_json(product) for product in ticket.products],
        "created_at": ticket.created_at.isoformat(),
    }
