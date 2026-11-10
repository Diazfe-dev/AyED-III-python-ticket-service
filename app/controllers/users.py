"""User management endpoints (admin only)."""

from flask import Blueprint
from flask.typing import ResponseReturnValue

from app.auth import admin_required, authenticated_user, get_user_service
from app.controllers.serializers import json_body, user_json

bp = Blueprint("users", __name__)

UPDATABLE_KEYS = ("name", "email", "preferred_channel")


@bp.post("/users")
@admin_required
def create_user() -> ResponseReturnValue:
    body = json_body()
    user = get_user_service().create_user(
        name=body.get("name"),
        email=body.get("email"),
        role=body.get("role"),
        password=body.get("password"),
        preferred_channel=body.get("preferred_channel"),
    )
    return user_json(user), 201


@bp.patch("/users/<int:user_id>")
@admin_required
def update_user(user_id: int) -> ResponseReturnValue:
    body = json_body()
    changes = {key: body[key] for key in UPDATABLE_KEYS if key in body}
    return user_json(get_user_service().update_user(user_id, **changes))


@bp.post("/users/<int:user_id>/deactivate")
@admin_required
def deactivate_user(user_id: int) -> ResponseReturnValue:
    user = get_user_service().deactivate_user(user_id, actor=authenticated_user())
    return user_json(user)


@bp.get("/clients")
@admin_required
def list_clients() -> ResponseReturnValue:
    return _users_of_role("Client")


@bp.get("/representatives")
@admin_required
def list_representatives() -> ResponseReturnValue:
    return _users_of_role("Representative")


def _users_of_role(role: str) -> ResponseReturnValue:
    return [user_json(user) for user in get_user_service().list_by_role(role)]
