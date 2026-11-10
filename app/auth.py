"""Authentication glue between Flask and the user service: session user and access guards."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import g, jsonify, session
from flask.typing import ResponseReturnValue

from app.db import get_session
from app.domain.users import Admin, User
from app.repositories.user_repository import SqlAlchemyUserRepository
from app.services.passwords import WerkzeugPasswordHasher
from app.services.user_service import UserService

USER_ID_KEY = "user_id"
CURRENT_USER_KEY = "current_user"

View = Callable[..., ResponseReturnValue]


def get_user_service() -> UserService:
    """Build the user service of the current request (or CLI command)."""
    db_session = get_session()
    return UserService(
        SqlAlchemyUserRepository(db_session), WerkzeugPasswordHasher(), db_session.commit
    )


def current_user() -> User | None:
    """The active user of the session; an unknown or inactive user counts as no session."""
    if CURRENT_USER_KEY not in g:
        user_id = session.get(USER_ID_KEY)
        user = None if user_id is None else get_user_service().find_active_user(user_id)
        setattr(g, CURRENT_USER_KEY, user)
    return getattr(g, CURRENT_USER_KEY)


def authenticated_user() -> User:
    """The session user inside a view guarded by `login_required` or `admin_required`."""
    user = current_user()
    if user is None:
        raise RuntimeError("authenticated_user() used in a view without login_required.")
    return user


def login_required(view: View) -> View:
    """Reject requests without an authenticated user with `401`."""

    @wraps(view)
    def guarded(*args: Any, **kwargs: Any) -> ResponseReturnValue:
        if current_user() is None:
            return jsonify(error="authentication_required"), 401
        return view(*args, **kwargs)

    return guarded


def admin_required(view: View) -> View:
    """Reject requests without a session with `401` and non-admin users with `403`."""

    @wraps(view)
    @login_required
    def guarded(*args: Any, **kwargs: Any) -> ResponseReturnValue:
        if not isinstance(current_user(), Admin):
            return jsonify(error="forbidden"), 403
        return view(*args, **kwargs)

    return guarded
