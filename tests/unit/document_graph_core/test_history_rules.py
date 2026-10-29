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
    ("Status", "Inbox", "Completed", False),  # skips the review
    ("Status", "Awaiting decision", "Inbox", False),  # capture creates items; it isn't a move
    ("Status", "Parked", "Inbox", True),  # unpark
    ("Status", "Approved", "Parked", True),  # revise a decided decision
    ("Status", "Researching", "Parked", False),  # a run is open; revise doesn't apply
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


# Register IDs (HOR-6): validation and the ownership rule, without a database.

def test_register_ids_and_names_are_normalised():
    assert history.register_id(" 25 ") == "25" and history.register_id(5.0) == "5"
    for bad in ("D-5", "0", "-1", "", "2.5"):
        with pytest.raises(ValueError):
            history.register_id(bad)
    with pytest.raises(ValueError, match="register must be one of"):
        asyncio.run(history.reserve_id("ws", "pipeline"))  # Pipeline IDs come from the Apps Script form


def test_a_pipeline_reservation_needs_its_run_and_the_reverse():
    with pytest.raises(ValueError, match="run_id is required"):
        asyncio.run(history.reserve_id("ws", "decision", 40))
    with pytest.raises(ValueError, match="pipeline_id is required"):
        asyncio.run(history.reserve_id("ws", "document", None, "R-3"))


def test_links_to_the_same_drive_file_compare_equal():
    a = "https://docs.google.com/document/d/16HPkIvjhCpaoMoGgvj7MOJBjqOVC829TYboOMC/edit"
    assert history.drive_key(a) == history.drive_key(a.replace("/edit", "/view?usp=drivesdk"))
    assert history.drive_key("https://drive.google.com/open?id=1aHCLHWuFYV2KVf75") == "1aHCLHWuFYV2KVf75"


@pytest.mark.parametrize("register, owner, conflicts", [
    ("decision", {"pipeline_id": "40"}, 1),  # another item's decision
    ("decision", {"pipeline_id": "42"}, 0),  # its own
    ("decision", {"pipeline_id": ""}, 0),  # an owner with no item yet doesn't block
    ("document", {"pipeline_id": "42", "drive_url": "https://docs.google.com/document/d/AAAAAAAAAAAA/edit"}, 1),
    ("document", {"pipeline_id": "40", "drive_url": "https://docs.google.com/document/d/AAAAAAAAAAAA/edit"}, 2),
    ("document", {"pipeline_id": "42", "drive_url": "https://docs.google.com/document/d/BBBBBBBBBBBB/view"}, 0),
    ("decision", None, 0),  # nobody has the ID
])
def test_ownership_conflicts(register, owner, conflicts):
    found = history.ownership_conflicts(register, "42", "https://docs.google.com/document/d/BBBBBBBBBBBB/edit",
                                        ("The live sheet row", owner))
    assert len(found) == conflicts


def test_a_document_write_needs_its_drive_url():
    with pytest.raises(ValueError, match="drive_url is required"):
        asyncio.run(history.check_register_write("ws", "document", 25, 40))
