"""Login, logout, session identity and own-password endpoints."""

from flask import Blueprint, session
from flask.typing import ResponseReturnValue

from app.auth import USER_ID_KEY, authenticated_user, get_user_service, login_required
from app.controllers.serializers import json_body, session_user_json

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login() -> ResponseReturnValue:
    body = json_body()
    user = get_user_service().authenticate(body.get("email"), body.get("password"))
    session.clear()
    session[USER_ID_KEY] = user.id
    return session_user_json(user)


@bp.post("/logout")
@login_required
def logout() -> ResponseReturnValue:
    session.clear()
    return "", 204


@bp.get("/me")
@login_required
def me() -> ResponseReturnValue:
    return session_user_json(authenticated_user())


@bp.post("/me/password")
@login_required
def change_own_password() -> ResponseReturnValue:
    body = json_body()
    get_user_service().change_own_password(
        authenticated_user(), body.get("current_password"), body.get("new_password")
    )
    return "", 204
