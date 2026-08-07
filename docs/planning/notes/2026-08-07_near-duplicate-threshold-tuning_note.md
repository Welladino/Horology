# Implementation Note

## Topic
- near-duplicate-threshold-tuning

## Context

First real end-to-end run of `code-sentinel`'s near-duplicate signaling (item 4 of `2026-08-07_document-graph-completeness-punch-list_note.md`, threshold originally set at 0.95 without real data): dispatched a fresh kanban task to `code-sentinel` for a repo health check, one day after its last real report (doc #7, 2026-08-06), to see how the new instruction behaved against genuine recurring content rather than a hypothetical.

## Decision

Lowered the near-duplicate threshold from **0.95 to 0.90** in both `CLAUDE.md` and `personas/subagents/code-sentinel.md`, synced to the running container.

**What happened on the test run:** `code-sentinel` wrote a new document (doc #8, "Repo Health Report ... 2026-08-07") rather than suppressing it — correct, matches the explicit "don't decide not to write it" instruction. It called `auto_link_similar_documents`, which correctly created a `related_to` edge to doc #7 at a real, verified cosine similarity of **0.9343** (confirmed independently by querying `document_embeddings` directly with the same `<=>` operator the tool itself uses — not just trusting the agent's self-report). Its `kanban_complete` summary used the words "near-duplicate of doc #7 (similarity 0.9343)" — but 0.9343 is below the *original* 0.95 bar, meaning the agent applied "near-duplicate" as a substantive content judgment rather than a strict readout of the numeric rule as written.

The underlying case is real and correctly identified: `Article_aggregator_agent` has been dormant since 2026-06-08, so two reports one day apart describe the same 30 Dependabot alerts, the same missing CI pipeline, and the same recommended actions — genuinely a near-duplicate in substance. The instruction's *spirit* held even though the *literal* threshold didn't fire. Concluded the threshold, not the agent's behavior, was miscalibrated — lowered it to 0.90, which would have correctly triggered on this exact case.

## Rationale

One real data point isn't a lot to retune from, but it's a real, verified one (independently recomputed, not just taken on the agent's word), and the direction of the miss was unambiguous — a case everyone would call a duplicate scored below the bar meant to catch duplicates. 0.90 was chosen as a round number clearly below 0.9343 with some margin, not derived from a distribution (there isn't one yet — only one real recurring pair exists in the document graph so far). This is a first-pass correction, not a final calibration.

## Impact

- `CLAUDE.md` and `personas/subagents/code-sentinel.md` both updated (0.95 → 0.90), `code-sentinel.md` re-synced to the running container's `/opt/data/profiles/code-sentinel/SOUL.md`.
- Real documents now in the graph: doc #8 (today's report), linked `related_to` doc #7 at 0.9343 — this pair is itself the calibration data point for any future threshold revisit.
- No change to the 0.85 auto-link threshold — that one already correctly fired on this pair (0.9343 > 0.85) and wasn't in question here.

## Follow-Ups

- Still only one real recurring-report data point. Revisit again once `code-sentinel` has run daily for a week or two (already flagged in the original punch-list note) — 0.90 may still be off in either direction once there's an actual distribution of day-over-day scores to look at, rather than one sample.
- Worth watching whether a *genuinely* newsworthy change (a new CVE, a merged PR) produces a score meaningfully below 0.90 on the same repo — that's the other half of calibration (avoiding false negatives on real news), not just catching false "nothing changed" duplicates, and hasn't been tested yet since the repo has had no real activity since 2026-06-08.
