from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable

from app.domain.errors import InvalidTransitionError
from app.domain.states import STATES, ClosedState, InProgressState, NewState, State
from app.domain.ticket import Ticket

TRANSITIONS = ("close", "reopen", "in_progress")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_base_state_rejects_every_transition(transition: str):
    """SPEC-TKT-13 · TC-TKT-13c"""
    with pytest.raises(InvalidTransitionError):
        getattr(State(), transition)(None, None, NOW)


@pytest.mark.parametrize(
    ("state_class", "allowed"),
    [
        (NewState, {"close", "in_progress"}),
        (InProgressState, {"close"}),
        (ClosedState, {"reopen"}),
    ],
)
def test_each_concrete_state_overrides_only_its_own_transitions(
    state_class: type[State], allowed: set[str]
):
    """SPEC-TKT-13 · TC-TKT-13c"""
    overridden = {name for name in TRANSITIONS if name in vars(state_class)}

    assert overridden == allowed


def test_state_is_a_read_only_property_backed_by_a_registry_of_plain_classes():
    """SPEC-TKT-14 · TC-TKT-14e"""
    ticket = Ticket(state_name="New")

    with pytest.raises(AttributeError):
        ticket.state = ClosedState()
    assert set(STATES) == {"New", "InProgress", "Closed"}
    assert isinstance(ticket.state, NewState)
    with pytest.raises(NoInspectionAvailable):
        inspect(NewState)
