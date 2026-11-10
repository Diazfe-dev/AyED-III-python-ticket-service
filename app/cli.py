"""Management commands of the application."""

import click
from flask import Flask
from flask.cli import with_appcontext

from app.auth import get_user_service
from app.domain.errors import DomainError


def register_commands(app: Flask) -> None:
    app.cli.add_command(create_admin_command)


@click.command("create-admin")
@click.option("--name", required=True, help="Name of the administrator.")
@click.option("--email", required=True, help="Email used to log in.")
@click.password_option(help="Asked for twice and hidden; never pass it on the command line.")
@with_appcontext
def create_admin_command(name: str, email: str, password: str) -> None:
    """Create an administrator with the same rules as any other user."""
    try:
        get_user_service().create_user(name=name, email=email, role="Admin", password=password)
    except DomainError as error:
        raise click.ClickException(str(error)) from error
    click.echo("Admin created.")
