"""User management and listing endpoints."""

from collections.abc import Callable
from typing import Any

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app.auth import admin_required, authenticated_user, get_user_service, login_required
from app.controllers.listing import listing_json
from app.controllers.serializers import json_body, party_json, user_json
from app.domain.users import User

bp = Blueprint("users", __name__)

UPDATABLE_KEYS = ("name", "email", "preferred_channel")
CLIENT_VIEWS: dict[str, Callable[[User], dict[str, Any]]] = {
    "Admin": user_json,
    "Representative": party_json,
}


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


@bp.post("/users/<int:user_id>/activate")
@admin_required
def activate_user(user_id: int) -> ResponseReturnValue:
    return user_json(get_user_service().activate_user(user_id))


@bp.post("/users/<int:user_id>/password")
@admin_required
def reset_password(user_id: int) -> ResponseReturnValue:
    get_user_service().reset_password(user_id, json_body().get("new_password"))
    return "", 204


@bp.get("/users")
@admin_required
def list_users() -> ResponseReturnValue:
    return _listing()


@bp.get("/clients")
@login_required
def list_clients() -> ResponseReturnValue:
    actor = authenticated_user()
    clients = get_user_service().list_clients(actor, **_listing_args())
    return listing_json(clients, CLIENT_VIEWS[actor.role])


@bp.get("/representatives")
@admin_required
def list_representatives() -> ResponseReturnValue:
    return _listing(role="Representative")


def _listing(role: str | None = None) -> ResponseReturnValue:
    return listing_json(get_user_service().list_users(role=role, **_listing_args()), user_json)


def _listing_args() -> dict[str, str | None]:
    return {name: request.args.get(name) for name in ("is_active", "q", "page", "page_size")}
