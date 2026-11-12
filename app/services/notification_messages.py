"""Texts of the notifications; pure functions, one per event."""

from app.domain.ticket import Ticket


def ticket_created(ticket: Ticket) -> str:
    return f"Ticket #{ticket.id} was created."


def milestone_added(ticket: Ticket) -> str:
    return f"Ticket #{ticket.id} has a new milestone."


def milestone_and_state_changed(ticket: Ticket) -> str:
    return f"Ticket #{ticket.id} has a new milestone and its state changed to {ticket.state_name}."


def ticket_closed(ticket: Ticket) -> str:
    return f"Ticket #{ticket.id} was closed. New state: {ticket.state_name}."


def ticket_reopened(ticket: Ticket) -> str:
    return f"Ticket #{ticket.id} was reopened. New state: {ticket.state_name}."
