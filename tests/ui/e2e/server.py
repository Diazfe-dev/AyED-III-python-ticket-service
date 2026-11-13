"""Real Flask server for the Playwright suite: temporary database and seeded data."""

import os
import secrets
import tempfile

from flask import Flask

from app import create_app
from app.auth import get_user_service
from app.db import create_schema, get_engine
from app.domain.base import Base
from app.wiring import get_catalog_service, get_product_service, get_ticket_service

DEFAULT_PORT = 5051
EXTRA_TICKETS = 25
PASSWORD = "Clave-segura-123"
ADMIN_EMAIL = "marta.ruiz@example.com"
REP_EMAIL = "raul.perez@example.com"
CLIENT_EMAIL = "ana.gomez@example.com"
SECOND_REP_EMAIL = "lucia.sosa@example.com"
SECOND_CLIENT_EMAIL = "diego.paz@example.com"


def build_app() -> Flask:
    """Create the app on a temporary SQLite file and seed it through the services."""
    folder = tempfile.mkdtemp(prefix="e2e-")
    app = create_app(
        {
            "SECRET_KEY": secrets.token_hex(32),
            "DATABASE_URL": f"sqlite:///{folder}/e2e.db",
        }
    )
    with app.app_context():
        create_schema(get_engine(), Base.metadata)
        _seed()
    return app


def _seed() -> None:
    users = get_user_service()
    users.create_user("Marta Ruiz", ADMIN_EMAIL, "Admin", PASSWORD)
    rep = users.create_user("Raúl Pérez", REP_EMAIL, "Representative", PASSWORD)
    users.create_user("Lucía Sosa", SECOND_REP_EMAIL, "Representative", PASSWORD)
    client = users.create_user("Ana Gómez", CLIENT_EMAIL, "Client", PASSWORD)
    users.create_user("Diego Paz", SECOND_CLIENT_EMAIL, "Client", PASSWORD)
    product_ids = _seed_catalog()
    tickets = get_ticket_service()
    for index in range(EXTRA_TICKETS):
        tickets.create_ticket(client.id, [product_ids[0]], f"Consulta número {index + 1}", rep)
    detailed = tickets.create_ticket(client.id, product_ids, "No enciende el equipo", rep)
    tickets.add_milestone(detailed.id, "Revisamos el cargador", rep, start_progress=True)
    tickets.add_milestone(detailed.id, "Sigue sin encender", client)


def _seed_catalog() -> list[int]:
    catalog = get_catalog_service()
    products = get_product_service()
    category = catalog.create_category("Computación")
    product_type = catalog.create_product_type("Portátiles", category.id)
    return [
        products.create_product("Notebook Lenovo", product_type.id).id,
        products.create_product("Notebook Dell", product_type.id).id,
    ]


def main() -> None:
    port = int(os.environ.get("E2E_PORT", DEFAULT_PORT))
    build_app().run(host="127.0.0.1", port=port, threaded=True)


if __name__ == "__main__":
    main()
