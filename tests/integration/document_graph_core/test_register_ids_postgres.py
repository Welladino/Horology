"""Register ID allocator and ownership check against a disposable migrated Postgres, as the horology_graph login.

HOR-6: four parallel runs took Decision and Document IDs as "max + 1" from the sheet and one silently
overwrote another's rows. reserve_id must hand out unique IDs under concurrency, respect rows added by
hand, and check_register_write must refuse a write to an ID owned by another item or Drive file."""
import asyncio
import uuid

import graph_core
from graph_core.history import service as history

# Fresh each session: the service login can't delete runs or reservations, by design.
WS = f"register-ids-test-{uuid.uuid4().hex[:8]}"
DOC_A = "https://docs.google.com/document/d/AAAAAAAAAAAAAAAAAAAA/edit"
DOC_B = "https://docs.google.com/document/d/BBBBBBBBBBBBBBBBBBBB/edit"


def with_database(dsn, body, pool=8):
    from horology_runtime.database import Database

    async def clean(db):
        async with db.transaction() as conn, conn.cursor() as cur:
            await cur.execute("DELETE FROM run_outputs WHERE run_id IN (SELECT id FROM run_log WHERE workspace = %s)", (WS,))
            for table in ("pipeline_events", "pipeline_items", "decisions", "document_index"):
                await cur.execute(f"DELETE FROM {table} WHERE workspace = %s", (WS,))  # nosec B608: fixed table names

    async def run():
        async with Database(dsn, pool) as db:
            graph_core.configure(db)
            try:
                await clean(db)
                await body(db)
            finally:
                await clean(db)
                graph_core.configure(None)
    asyncio.run(run())


def decision(did, pid):
    return {"decision_id": did, "pipeline_id": pid, "status": "proposed", "review_stage": None, "decision": None,
            "reason": None, "rework_instructions": None, "data": {"Decision ID": did, "Pipeline ID": pid}}


def index_row(did, pid, url):
    return {"index_document_id": did, "pipeline_id": pid, "title": "Doc", "drive_url": url, "doc_type": "research",
            "document_status": "draft", "last_updated": None, "graph_inclusion": False, "graph_sync_status": None,
            "data": {"Document ID": did, "Pipeline ID": pid, "Drive URL": url}}


async def claim(pid):
    claimed = await history.claim(WS, pid, "Claude Code", "Cloud")
    assert claimed["claimed"] is True
    return claimed["run_id"]


def test_parallel_runs_get_unique_monotonic_ids(database):
    """The 28/10/2026 incident: items 39-42 ran at once. Each now reserves its own IDs."""
    async def body(db):
        # The synced copy already holds Decisions 1-4 and Documents up to 24, one added by hand with a gap.
        await history.apply_records(WS, decisions=[decision(str(n), "22") for n in range(1, 5)],
                                    index_rows=[index_row(str(n), "22", f"{DOC_A}?n={n}") for n in (1, 2, 24)])
        runs = {pid: await claim(pid) for pid in (39, 40, 41, 42)}

        async def run_reserves(pid):
            # Each run takes a decision and two documents, interleaved with the others.
            return [await history.reserve_id(WS, register, pid, runs[pid])
                    for register in ("document", "decision", "document")]

        results = await asyncio.gather(*(run_reserves(pid) for pid in (39, 40, 41, 42) for _ in range(2)))
        flat = [r for group in results for r in group]
        assert all(r["reserved"] for r in flat)
        decisions = sorted(int(r["id"]) for r in flat if r["register"] == "decision")
        documents = sorted(int(r["id"]) for r in flat if r["register"] == "document")
        # Unique and gap-free above what the sheet already had.
        assert decisions == list(range(5, 5 + 8))
        assert documents == list(range(25, 25 + 16))

        # A row added by hand past the counter, then synced, moves the next ID past it.
        await history.apply_records(WS, index_rows=[index_row("60", None, f"{DOC_A}?n=60")])
        assert (await history.reserve_id(WS, "document", 40, runs[40]))["id"] == "61"
        # So does one the agent has just read in the live sheet, before any sync.
        assert (await history.reserve_id(WS, "document", 40, runs[40], live_max=70))["id"] == "71"
        assert (await history.reserve_id(WS, "decision", 40, runs[40], live_max=3))["id"] == "13"

        # Who took which ID is in the item's history at once, without waiting for a sync.
        item = await history.item_history(WS, 40)
        mine = [(r["register"], r["id"], r["run_id"]) for r in item["reserved_ids"]]
        assert len(mine) == 2 * 3 + 3 and all(run == runs[40] for _, _, run in mine)
        assert any(entry["what"] == "id_reserved" for entry in item["timeline"])
        other = {r["id"] for r in (await history.item_history(WS, 42))["reserved_ids"] if r["register"] == "decision"}
        assert not other & {i for reg, i, _ in mine if reg == "decision"}
        for run in runs.values():
            await history.finish(WS, run, "done")
    with_database(database, body)


def test_many_concurrent_reservations_on_one_register(database):
    """More callers than pool connections, all on one register: every ID is distinct and consecutive."""
    async def body(db):
        results = await asyncio.gather(*(history.reserve_id(WS, "decision") for _ in range(24)))
        ids = sorted(int(r["id"]) for r in results)
        assert ids == list(range(ids[0], ids[0] + 24))
    with_database(database, body, pool=6)


def test_reservations_need_the_live_run_of_that_item(database):
    async def body(db):
        run = await claim(50)
        refused = await history.reserve_id(WS, "decision", 51, run)
        assert refused["reserved"] is False and "belongs to Pipeline item 50" in refused["reason"]
        await history.finish(WS, run, "done")
        finished = await history.reserve_id(WS, "decision", 50, run)
        assert finished["reserved"] is False and "not live" in finished["reason"]
        missing = await history.reserve_id(WS, "decision", 50, "R-999999999")
        assert missing["reserved"] is False and "No run" in missing["reason"]
        # Refusals hand out nothing: the next ID is still the first one.
        first = await history.reserve_id(WS, "document")
        assert first["reserved"] is True and first["run_id"] is None
    with_database(database, body)


def test_a_collision_stops_the_write_instead_of_overwriting(database):
    """Item 42 tried to write Decision 5 and Document 25 after item 40 had: it must be stopped."""
    async def body(db):
        run40, run42 = await claim(40), await claim(42)
        doc = (await history.reserve_id(WS, "document", 40, run40))["id"]
        dec = (await history.reserve_id(WS, "decision", 40, run40))["id"]

        # Item 40 writes its rows: the first check binds the Drive file to the reservation.
        assert (await history.check_register_write(WS, "document", doc, 40, DOC_A))["ok"] is True
        assert (await history.check_register_write(WS, "decision", dec, 40))["ok"] is True
        # Re-saving its own row (another link form of the same file) is fine.
        again = await history.check_register_write(WS, "document", doc, 40, DOC_A.replace("/edit", "/view?usp=x"),
                                                    live_row={"pipeline_id": "40", "drive_url": DOC_A})
        assert again["ok"] is True

        # Item 42 picked the same IDs from the sheet: stopped, before the sheet is even synced.
        clash = await history.check_register_write(WS, "document", doc, 42, DOC_B)
        assert clash["ok"] is False and clash["reason"] == "id_owned_by_another_row"
        assert "Pipeline item 40, not 42" in clash["message"] and "different Drive file" in clash["message"]
        assert "don't write this row" in clash["next_step"]
        assert (await history.check_register_write(WS, "decision", dec, 42))["ok"] is False

        # A row in the live sheet that nobody reserved (added by hand) is protected too.
        live = await history.check_register_write(WS, "decision", 99, 42, live_row={"pipeline_id": "41"})
        assert live["ok"] is False and "live sheet row" in live["message"]
        # ...and so is one only the last sync has seen.
        await history.apply_records(WS, index_rows=[index_row("98", "39", DOC_A)])
        synced = await history.check_register_write(WS, "document", 98, 39, DOC_B)
        assert synced["ok"] is False and "last synced copy" in synced["message"]
        # A new ID that wasn't reserved is allowed but flagged.
        loose = await history.check_register_write(WS, "decision", 500, 42)
        assert loose["ok"] is True and "reserve_id" in loose["warning"]

        # Item 42 reserves its own instead and writes without a clash.
        own = (await history.reserve_id(WS, "document", 42, run42))["id"]
        assert own != doc
        assert (await history.check_register_write(WS, "document", own, 42, DOC_B))["ok"] is True
    with_database(database, body)
