"""Execution-history rules with no database: workflow checks, IDs and argument validation."""
import asyncio

import pytest

from graph_core.history import service as history, workflow


def test_workflow_values_come_from_workflow_yaml():
    assert workflow.values("Agent status") == ["No action", "Plan", "Ready"]
    assert workflow.values("Run location") == ["Local", "Cloud"]
    assert workflow.values("Not a field") is None


@pytest.mark.parametrize("field, old, new, expected", [
    ("Status", "Ready", "Researching", True),  # start-run has no Status in "from"
    ("Status", "Researching", "Awaiting decision", True),
    ("Status", "Awaiting decision", "Approved", True),
    ("Status", "Inbox", "Handed off", False),  # skips the review
    ("Status", "Awaiting decision", "Inbox", False),  # capture creates items; it isn't a move
    ("Status", "Parked", "Inbox", True),  # unpark
    ("Agent status", "Plan", "No action", True),  # planned
    ("Agent status", "Ready", "Plan", False),
    ("Run location", "Local", "Cloud", None),  # no transition governs it
])
def test_a_change_is_checked_against_the_transitions(field, old, new, expected):
    assert workflow.expected(field, old, new) is expected


def test_ids_are_normalised():
    assert history.item_id(42) == "42"
    assert history.item_id("42.0") == "42"
    assert history.parse_run_id("r-7") == 7 and history.parse_run_id(7) == 7
    for bad in ("0", "-3", "abc", ""):
        with pytest.raises(ValueError):
            history.item_id(bad)
    with pytest.raises(ValueError):
        history.parse_run_id("run 7")


@pytest.mark.parametrize("kwargs, message", [
    ({"agent_type": "ChatGPT"}, "agent_type"),
    ({"run_location": "Moon"}, "Run location"),
    ({"kind": "review"}, "kind"),
])
def test_claims_are_validated_before_any_database_call(kwargs, message):
    args = {"agent_type": "Claude Code", "run_location": "Local", "kind": "run", **kwargs}
    with pytest.raises(ValueError, match=message):
        asyncio.run(history.claim("ws", 42, **args))


def test_finish_needs_a_known_status():
    with pytest.raises(ValueError, match="status"):
        asyncio.run(history.finish("ws", "R-1", "complete"))
