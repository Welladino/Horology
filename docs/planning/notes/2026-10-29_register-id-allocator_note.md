# Register ID allocator and ownership check (HOR-6)

## Context

On 28/10/2026 four cloud runs (Pipeline items 39–42, runs R-12 to R-15) ran in parallel. Each specialist allocated Decision and Document IDs as "read the register, take max + 1, upsert by ID", with nothing between the read and the write. Items 40 and 42 both took Decision 5 and Document 25; item 42 wrote last, so item 40's Decision Register and Document Index rows were replaced without an error. Item 40's Direction document still exists in Drive, but no register row points to it, and its Pipeline row names item 42's decision and document. Item 39 hit the same clash and moved its research document to ID 29. Because the write was an upsert, the collision overwrote instead of duplicating, so the sync job's duplicate Document ID check never fired. Separately, item 41's run briefly wrote Researching / Stage 1 to item 40's Pipeline row: rows were sometimes located by position. The skills had flagged that a coordinated allocator was required before parallel writers.

## Decision

- **Allocator in the document graph,** next to `claim_item`: `reserve_id(register, pipeline_id, run_id, live_max_id)` for `decision` and `document`. One statement upserts the workspace's counter in `register_ids` to greatest(last + 1, highest numeric ID in the synced sheet copy + 1, live maximum + 1); the row lock serialises concurrent callers. Each reservation is recorded in `register_reservations` with its Pipeline item and run, and `get_item_history` lists them immediately (migration `20261029_010`).
- **Ownership check before every register write:** `check_register_write` compares the intended Pipeline ID and Drive file with the live row the agent just found by ID, the synced copy and the reservation. A difference returns `ok: false` with a plain message; the agent stops and reports instead of overwriting. The first clean check of a Document ID binds its Drive URL to the reservation, so a second writer is refused before the next sync.
- **Rows by ID only:** skills now say to find every row by its ID immediately before writing. The Apps Scripts (decision apply and page, Pipeline edits, ClickUp Document count, Locations check) re-find the row by ID (Locations: folder ID) just before each write and stop on a missing or duplicated ID, instead of writing to the row number read earlier.
- Skills (research linking rules, technical assessment, GTM, marketing strategy, content planner, security review, synthesis, supervisor, capture-triage records, digest, watcher prompt, document-graph) call `reserve_id` instead of taking the next unused ID; the "coordinated allocator is required" caveats are removed. `workflow.yaml` gains a `register_ids` section.

## Rationale

- Neon already holds the run claims and a copy of each register, so the allocator lives beside `claim_item` and needs no new service or credential. A Sheets-side lock would only cover Apps Script, not agents writing through the Sheets connector.
- Taking the maximum with the synced and live sheet IDs respects rows the founder adds by hand, so the counter needs no seeding and can't fall behind the sheet.
- The ownership check catches the remaining risk an allocator can't: a writer that read a stale ID or skipped `reserve_id`.

## Out of scope and limits

- Pipeline IDs: the Add Pipeline item form already allocates them under its script lock.
- The tools can't force an agent to call them; the skills require both, and the sync's duplicate-ID check still catches duplicated rows.
- Unused reservations leave gaps in the numbering. IDs stay unique and only increase.

## Verification

- Integration tests against disposable PostgreSQL (`tests/integration/document_graph_core/test_register_ids_postgres.py`): four parallel runs and 24 concurrent callers get unique, gap-free IDs above the sheet's highest; hand-added and live IDs are respected; reservations need the item's live run; a forced collision on another item's Decision or Document ID is refused with a clear message.
- Unit tests for the ownership rule, tool registration, `workflow.yaml` and a guard against "next unused ID" wording in skills; Apps Script tests for by-ID writes after a row moves.
- The migration upgrades and downgrades cleanly on a disposable database. It has not been applied to Neon.

## Follow-ups

- Apply migration `20261029_010` to Neon, then deploy the document-graph service and republish the skills.
- Restore item 40's Decision Register and Document Index rows under new reserved IDs and repoint its Pipeline row (listed in the HOR-6 pull request).
