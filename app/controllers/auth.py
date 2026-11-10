"""Login and logout endpoints."""

from flask import Blueprint, session
from flask.typing import ResponseReturnValue

from app.auth import USER_ID_KEY, get_user_service, login_required
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
