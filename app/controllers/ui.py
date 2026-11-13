"""Public route that serves the single-page interface."""

from flask import Blueprint, Response, current_app

bp = Blueprint("ui", __name__)


@bp.get("/")
def index() -> Response:
    return current_app.send_static_file("index.html")
