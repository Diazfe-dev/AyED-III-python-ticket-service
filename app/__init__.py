"""Flask application factory."""

import os
from collections.abc import Mapping
from typing import Any

from flask import Flask

from app import db
from app.config import load_config
from app.controllers import health


def create_app(overrides: Mapping[str, Any] | None = None) -> Flask:
    """Build a configured application instance."""
    app = Flask(__name__)
    app.config.from_mapping(load_config(os.environ, overrides, app.instance_path))
    _ensure_instance_folder(app)
    db.init_app(app)
    app.register_blueprint(health.bp)
    return app


def _ensure_instance_folder(app: Flask) -> None:
    if app.instance_path in app.config["DATABASE_URL"]:
        os.makedirs(app.instance_path, exist_ok=True)
