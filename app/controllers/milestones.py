"""Milestone endpoints (the MilestoneController): HTTP in and out, the rules live in the service."""

from flask import Blueprint
from flask.typing import ResponseReturnValue

from app.auth import authenticated_user, login_required
from app.controllers.serializers import json_body, milestone_json
from app.wiring import get_ticket_service

bp = Blueprint("milestones", __name__)


@bp.post("/tickets/<int:ticket_id>/milestones")
@login_required
def add_milestone(ticket_id: int) -> ResponseReturnValue:
    body = json_body()
    milestone = get_ticket_service().add_milestone(
        ticket_id,
        body.get("content"),
        authenticated_user(),
        start_progress=body.get("start_progress", False),
    )
    return milestone_json(milestone), 201


@bp.get("/tickets/<int:ticket_id>/milestones")
@login_required
def list_milestones(ticket_id: int) -> ResponseReturnValue:
    milestones = get_ticket_service().list_milestones(ticket_id, authenticated_user())
    return [milestone_json(milestone) for milestone in milestones]
