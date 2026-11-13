"""Ticket endpoints (the TicketController): HTTP in and out, the rules live in the service."""

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app.auth import authenticated_user, login_required
from app.controllers.listing import listing_json
from app.controllers.serializers import json_body, state_change_json, ticket_json
from app.wiring import get_ticket_service

bp = Blueprint("tickets", __name__)

LISTING_ARGS = ("state", "client_id", "representative_id", "q", "order", "page", "page_size")


@bp.post("/tickets")
@login_required
def create_ticket() -> ResponseReturnValue:
    body = json_body()
    ticket = get_ticket_service().create_ticket(
        client_id=body.get("client_id"),
        product_ids=body.get("product_ids"),
        first_message=body.get("first_message"),
        actor=authenticated_user(),
    )
    return ticket_json(ticket), 201


@bp.get("/tickets")
@login_required
def list_tickets() -> ResponseReturnValue:
    args = {name: request.args.get(name) for name in LISTING_ARGS}
    return listing_json(
        get_ticket_service().list_tickets(authenticated_user(), **args), ticket_json
    )


@bp.get("/tickets/<int:ticket_id>")
@login_required
def get_ticket(ticket_id: int) -> ResponseReturnValue:
    return ticket_json(get_ticket_service().get_ticket(ticket_id, authenticated_user()))


@bp.get("/tickets/<int:ticket_id>/state-changes")
@login_required
def list_state_changes(ticket_id: int) -> ResponseReturnValue:
    changes = get_ticket_service().list_state_changes(ticket_id, authenticated_user())
    return [state_change_json(change) for change in changes]


@bp.post("/tickets/<int:ticket_id>/close")
@login_required
def close_ticket(ticket_id: int) -> ResponseReturnValue:
    return ticket_json(get_ticket_service().close_ticket(ticket_id, authenticated_user()))


@bp.post("/tickets/<int:ticket_id>/reopen")
@login_required
def reopen_ticket(ticket_id: int) -> ResponseReturnValue:
    return ticket_json(get_ticket_service().reopen_ticket(ticket_id, authenticated_user()))


@bp.post("/tickets/<int:ticket_id>/products")
@login_required
def add_ticket_products(ticket_id: int) -> ResponseReturnValue:
    ticket = get_ticket_service().add_products(
        ticket_id, json_body().get("product_ids"), authenticated_user()
    )
    return ticket_json(ticket)


@bp.delete("/tickets/<int:ticket_id>/products/<int:product_id>")
@login_required
def remove_ticket_product(ticket_id: int, product_id: int) -> ResponseReturnValue:
    get_ticket_service().remove_product(ticket_id, product_id, authenticated_user())
    return "", 204
