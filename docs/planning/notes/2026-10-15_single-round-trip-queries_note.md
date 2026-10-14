# Implementation Note

## Topic
- single-round-trip-queries

## Context
- Cloud Run (us-central1) to Neon (Singapore) costs about 0.2 s per database round trip ([earlier note](2026-10-13_fewer-database-round-trips_note.md)).
- Counted from the Postgres statement log on the throwaway database, one call of each graph tool made 80 round trips. Two thirds were `BEGIN` and `COMMIT`: every query ran in its own transaction, so a single read cost 3 trips. Some tools also fetched their data in several queries: `get_topic` made 12 trips, `auto_link_similar_documents` 19.
- From the code, an uncached paid gateway call (for example `tavily_search`) made about 13 trips: a cache check, a quota reservation of 5 statements, and a cache save.

## Decision
- **Autocommit connections.** `Database.connection()` runs one statement with no `BEGIN`/`COMMIT`; Postgres makes each statement atomic on its own. `Database.transaction()` is kept for work that must succeed or fail together.
- **One statement per read tool.** `get_topic`, `find_entity`, `entity_documents` and `link_documents` each became one query. They use JSON aggregation or CTEs; `link_documents` checks both documents and inserts in one statement. Their output on the trial data is byte-for-byte the same as before (13 topics, 8 name lookups, 15 entity cards with mentions).
- **Several statements, one round trip, where order matters.** Statements are sent together as one simple query, which Postgres runs as a single implicit transaction; psycopg's `AsyncClientCursor` quotes values client-side. This is used in three places:
  - storing a document's sections (vector, delete old sections, insert new);
  - the gateway quota reservation (lock, then check budgets and insert);
  - run requests, claims and hand-overs (lock, then check and claim).
- **Bulk writes.** Auto-link adds all new links in one insert, and topic placement is one insert that is skipped when there's nothing to place.

## Rationale
- **Why not one statement for the quota or claim checks.** A statement reads the data as of its start. One that waits for the lock would then sum totals from before the other reservation committed. Measured on the test database: 20 concurrent reservations against a daily cap of 3 let 4, 3, 4, 9 and 10 through as one statement, but exactly 3 every time as lock-then-check in one trip. The same holds for run claims: 10 concurrent requests start exactly one run.
- **Why sections are deleted, not updated in place.** Topic placements and entity mentions point at sections; they must go when the text changes.
- **Why not psycopg pipeline mode.** It could batch more, but its behaviour through Neon's PgBouncer pooler isn't verified. Plain SQL and simple queries are standard protocol.

## Impact
- Measured on the test database, one call of each graph tool now makes 17 round trips, down from 80. At 0.2 s each, that's about 3.4 s instead of 16 s. Most tools make 1 trip (was 3–12); `auto_link_similar_documents` makes 4 (was 19).
- An uncached paid gateway call makes 3 trips, down from about 13 (by the code; the gateway tests, including the concurrent-budget test, pass).
- The sync job benefits too: sections, links and placements are written in fewer trips.
- OAuth record writes clean up expired records in the same statement as the write.

## Follow-Ups
- After the deploy, run `scripts/ops/live_check.py` and the latency queries, and compare with the 2026-10-13 baseline.
