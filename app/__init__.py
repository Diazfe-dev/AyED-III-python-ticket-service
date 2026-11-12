"""Flask application factory."""

import os
from collections.abc import Mapping
from typing import Any

from flask import Flask

from app import db
from app.cli import register_commands
from app.config import load_config
from app.controllers import api_docs, auth, catalog, health, milestones, tickets, users
from app.controllers.errors import register_error_handlers


def create_app(overrides: Mapping[str, Any] | None = None) -> Flask:
    """Build a configured application instance."""
    app = Flask(__name__)
    app.config.from_mapping(load_config(os.environ, overrides, app.instance_path))
    _ensure_instance_folder(app)
    db.init_app(app)
    app.register_blueprint(health.bp)
    app.register_blueprint(api_docs.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(catalog.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(milestones.bp)
    register_error_handlers(app)
    register_commands(app)
    return app


def _ensure_instance_folder(app: Flask) -> None:
    if app.instance_path in app.config["DATABASE_URL"]:
        os.makedirs(app.instance_path, exist_ok=True)
