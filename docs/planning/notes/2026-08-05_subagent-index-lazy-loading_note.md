# Implementation Note

## Topic
- subagent-index-lazy-loading

## Context

After adding the first two subagent personas (GTM Manager, Marketing Executive) directly referenced by name/scope inside `SOUL.md`'s Delegation section, noticed a scaling problem: `SOUL.md` is sent as the system prompt on every single message in every session, so embedding each subagent's description directly into it means every new subagent permanently grows the token cost of every conversation, including ones that never delegate.

## Decision

Split subagent information into two layers instead of one:

- **`personas/subagents/INDEX.md`** — a short table: name, one-line scope, absolute file path. This is what `SOUL.md` tells Second-Soul to read first when deciding whether/which subagent fits a task.
- **`personas/subagents/<name>.md`** — the full persona (unchanged from before), read in full only once Second-Soul has already decided, from the index, which specific subagent it needs.

`SOUL.md` itself no longer names or describes individual subagents — it only points at the index and describes the two-step read pattern (index first, full persona only on decision). Adding a subagent going forward = one new line in `INDEX.md` + one new persona file; `SOUL.md` doesn't change.

This mirrors Hermes's own `skills` system, which already works this way (browse a lightweight catalog, only load full skill content when actually invoking one) — not a new idiom, just applying the platform's own pattern to our own persona layer.

**Bug found and fixed while verifying this:** the first version used a relative path (`personas/subagents/INDEX.md`) in `SOUL.md`'s instructions. Testing showed the agent's file-tool working directory is `/opt/hermes` (Hermes's own installed codebase), not `/opt/data` (our mounted volume) — so the relative path resolved against the wrong root and the agent correctly reported the file didn't exist. Fixed by using the absolute path `/opt/data/personas/subagents/INDEX.md` throughout, confirmed working via a live test query after the fix.

## Rationale

Caught before it became a real cost/latency problem — better to design the lazy-load pattern now, with two subagents, than retrofit it once SOUL.md is bloated with five or ten. Testing the fix live (rather than assuming the absolute path would work) caught a real bug — the working-directory assumption was wrong on the first attempt, which would have silently broken delegation for any subagent added under the naive relative-path version.

## Impact

- `SOUL.md` growth is now bounded regardless of subagent count — it grows by ~1 line (a delegation-flow description) rather than one full persona block per subagent.
- Establishes the standing convention: any file that references another persona/index file by path must use the absolute `/opt/data/...` form, not a relative one.

## Follow-Ups

- None outstanding for this pattern; verified working end-to-end.
- If the subagent roster grows large enough that even INDEX.md's table becomes unwieldy to scan, consider categorizing it (e.g. a `category` column) — not needed yet at 2 entries.
