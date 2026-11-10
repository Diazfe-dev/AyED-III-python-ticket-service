"""JSON input and output shared by the controllers."""

from typing import Any

from flask import request

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
