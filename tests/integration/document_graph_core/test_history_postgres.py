"""Execution history against a disposable migrated Postgres, as the horology_graph login:
claims, finishing runs, and the records pass (copies, events, run outputs, item history)."""
import asyncio
import uuid

import pytest

import graph_core
from graph_core.documents import service as documents
from graph_core.history import service as history

WS = f"history-test-{uuid.uuid4().hex[:8]}"  # fresh each session: the service login can't delete runs, by design
TABLES = ("pipeline_events", "pipeline_items", "decisions", "document_index")


def with_database(dsn, body):
    from horology_runtime.database import Database

    async def clean(db):
        async with db.transaction() as conn, conn.cursor() as cur:
            await cur.execute("DELETE FROM run_outputs WHERE run_id IN (SELECT id FROM run_log WHERE workspace = %s)", (WS,))
            for table in TABLES:
                await cur.execute(f"DELETE FROM {table} WHERE workspace = %s", (WS,))  # nosec B608: fixed table names
            await cur.execute("DELETE FROM documents WHERE workspace = %s", (WS,))

    async def run():
        async with Database(dsn, 6) as db:
            graph_core.configure(db)
            try:
                await clean(db)
                await body(db)
            finally:
                await clean(db)
                graph_core.configure(None)
    asyncio.run(run())


def item(pid="42", **fields):
    base = {"pipeline_id": pid, "title": "Pricing page", "domain": "Welladino", "type": "Research",
            "status": "Inbox", "stage": "Stage 0", "review_stage": None, "agent_status": "No action",
            "agent_type": "Claude Code", "run_location": None, "planner_output": None,
            "current_decision_id": None, "next_step": "Which tier first?"}
    base.update(fields)
    return {**base, "data": {k: v for k, v in base.items() if v is not None}}


def test_only_one_claim_wins_and_runs_finish_once(database):
    async def body(db):
        results = await asyncio.gather(*[history.claim(WS, 42, "Claude Code", "Local") for _ in range(5)])
        winners = [r for r in results if r["claimed"]]
        assert len(winners) == 1
        assert all(r["reason"] == "already_claimed" and r["run_id"] == winners[0]["run_id"]
                   for r in results if not r["claimed"])
        run_id = winners[0]["run_id"]

        # Another item is independent.
        assert (await history.claim(WS, 43, "Codex", "Cloud"))["claimed"] is True

        done = await history.finish(WS, run_id, "done", ["horology-research"], "1, 2", "Answered.", "session_1")
        assert done["finished"] is True and done["status"] == "done"
        again = await history.finish(WS, run_id, "failed")
        assert again == {"finished": False, "reason": "already_finished", "run_id": run_id, "status": "done"}
        with pytest.raises(ValueError, match="No run"):
            await history.finish("someone-else", run_id, "done")  # another workspace can't see it

        # A finished run frees the item; an expired claim does too.
        second = await history.claim(WS, 42, "Claude Code")
        assert second["claimed"] is True
        async with db.transaction() as conn, conn.cursor() as cur:
            await cur.execute("UPDATE run_log SET claim_expires = now() - interval '1 minute' WHERE id = %s",
                              (history.parse_run_id(second["run_id"]),))
        assert (await history.claim(WS, 42, "Claude Code"))["claimed"] is True

        runs = await history.list_runs(WS, 24)
        assert {r["status"] for r in runs} == {"done", "claimed"}
        assert any(r["expired"] for r in runs)  # the claim we aged
        assert [r["run_id"] for r in await history.list_runs(WS, 24, pipeline_id=43)]
    with_database(database, body)


def test_the_records_pass_records_changes_and_outputs(database):
    async def body(db):
        # Item 52: the first test's runs (item 42) stay, since the login can't delete runs.
        # First copy: a baseline, no events.
        first = await history.apply_records(WS, [item("52")], [], [])
        assert first["items"] == 1 and first["item_events"] == 0

        # The founder makes it Ready; a run claims it; the agent changes its status.
        await history.apply_records(WS, [item("52", agent_status="Ready", stage="Stage 1")], None, None)
        run = await history.claim(WS, 52, "Claude Code")
        assert run["claimed"] is True
        run_id = run["run_id"]
        await documents.write_agent_document(WS, "analysis", "Working note", "Notes.", "horology-research",
                                             pipeline_id=52)
        index_row = {"index_document_id": "7", "pipeline_id": "52", "title": "Pricing research",
                     "drive_url": "https://docs.google.com/document/d/abcdefghijk/edit", "doc_type": "research",
                     "document_status": "Draft", "last_updated": "2026-10-16", "graph_inclusion": False,
                     "graph_sync_status": None, "data": {"Document ID": "7", "Title": "Pricing research"}}
        decision = {"decision_id": "D-3", "pipeline_id": "52", "status": "proposed", "review_stage": "Stage 1",
                    "decision": None, "reason": None, "rework_instructions": None, "data": {"Decision ID": "D-3"}}
        counts = await history.apply_records(
            WS, [item("52", status="Awaiting decision", stage="Stage 2", review_stage="Stage 1", agent_status="No action")],
            [decision], [index_row])
        assert counts["item_events"] == 4  # Status, Stage, Review stage, Agent status
        assert counts["index_outputs"] == 1 and counts["agent_outputs"] == 1
        await history.finish(WS, run_id, "done", ["horology-research"])

        # The founder sends it back to the Inbox from review: no transition allows that.
        await history.apply_records(WS, [item("52", status="Inbox", stage="Stage 2", review_stage="Stage 1")],
                                    [{**decision, "status": "accepted", "data": {"Decision ID": "D-3", "x": 1}}],
                                    [index_row])

        story = await history.item_history(WS, 52)
        changes = [e for e in story["timeline"] if e["what"] == "change"]
        status_changes = [(e["from_value"], e["to_value"], e["expected"], e.get("run_id")) for e in changes
                          if e["field"] == "Status"]
        assert status_changes == [("Inbox", "Awaiting decision", False, run_id),  # Researching was skipped between syncs
                                  ("Awaiting decision", "Inbox", False, run_id)]
        assert ("Agent status", "No action", "Ready") in [(e["field"], e["from_value"], e["to_value"]) for e in changes]
        assert any(e["field"] == "Decision D-3 status" and e["to_value"] == "accepted" for e in changes)
        run_entry = next(e for e in story["timeline"] if e["what"] == "run")
        assert sorted(o["kind"] for o in run_entry["outputs"]) == ["agent", "index"]
        assert story["item"]["status"] == "Inbox"
        assert story["decisions"][0]["status"] == "accepted"
        documents_seen = [e for e in story["timeline"] if e["what"] == "document"]
        assert documents_seen[0]["index_document_id"] == "7" and documents_seen[0]["graph_document_id"] is None
    with_database(database, body)
