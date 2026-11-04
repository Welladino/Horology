"""Execution-history rules with no database: workflow checks, IDs and argument validation."""
import asyncio
from unittest.mock import AsyncMock

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


DOC = "https://docs.google.com/document/d/1m3YseqUX30ddXAc7mvAvB-qUSkaDRxvSIkBTD2BTidQ/edit"


@pytest.mark.parametrize("link, drive", [
    (DOC, True),
    ("https://docs.google.com/spreadsheets/d/1Il7NvidmZ5n4s3kzaCjEHT0tcE-2KcS5IYvffOtNIqY/edit#gid=0", True),
    ("https://docs.google.com/presentation/d/1AbCdEfGhIjKlMnOp/edit?usp=sharing", True),
    ("https://drive.google.com/file/d/1aHCLHWuFYV2KVf75wclJM-uZQ3c7fyNx/view", True),  # e.g. an HTML file
    ("https://drive.google.com/open?id=1aHCLHWuFYV2KVf75", True),
    ("https://github.com/Welladino/Article_aggregator_agent/compare/version_v1.8...claude/item-55?expand=1", False),
    ("https://github.com/Welladino/Article_aggregator_agent/blob/main/docs/planning/notes/note.md", False),
    ("https://drive.google.com/drive/folders/1mv8AzjLxR6ZQ9PN1zf_-t4rw_Qkfve0o", False),  # a folder, not a file
    ("https://docs.google.com.evil.example/document/d/1m3YseqUX30ddXAc7mvAvB/edit", False),
    ("http://docs.google.com/document/d/1m3YseqUX30ddXAc7mvAvB/edit", False),
    ("https://example.com/report", False),
])
def test_is_drive_file(link, drive):
    assert history.is_drive_file(link) is drive


def test_research_link_problems_reads_a_list_or_the_cell_text():
    gh = "https://github.com/Welladino/Horology/compare/main...x"
    assert history.research_link_problems(None) == []
    assert history.research_link_problems([DOC]) == []
    assert history.research_link_problems(f"{DOC}\n\n{gh}") == [gh]
    assert history.research_link_problems([DOC, gh]) == [gh]


def test_a_decision_with_a_github_research_link_is_refused_before_the_ownership_check(monkeypatch):
    repository = AsyncMock()
    monkeypatch.setattr(history, "_repository", lambda: repository)
    gh = "https://github.com/Welladino/Article_aggregator_agent/compare/version_v1.8...claude/item-55?expand=1"
    result = asyncio.run(history.check_register_write("ws", "decision", 13, 55, research_links=[DOC, gh]))
    assert result["ok"] is False and result["reason"] == "research_links_not_drive"
    assert result["links"] == [gh]
    repository.register_owner.assert_not_called()


def test_drive_research_links_go_on_to_the_ownership_check(monkeypatch):
    repository = AsyncMock()
    repository.register_owner.return_value = ({"pipeline_id": "55"}, None)
    monkeypatch.setattr(history, "_repository", lambda: repository)
    result = asyncio.run(history.check_register_write("ws", "decision", 13, 55, research_links=[DOC]))
    assert result["ok"] is True
    repository.register_owner.assert_awaited_once()


def test_research_links_are_only_for_the_decision_register():
    with pytest.raises(ValueError, match="only for a Decision Register"):
        asyncio.run(history.check_register_write("ws", "document", 25, 40, DOC, research_links=[DOC]))
