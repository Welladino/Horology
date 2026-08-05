# Implementation Note

## Topic
- stale-skill-cleanup

## Context

The founder asked whether the original `write-document` skill (the discarded code-execution approach, holding a raw Neon credential in `.mjs` scripts run via terminal/code_execution) still had leftover references anywhere. It did — `hermes-data/skills/document-graph/write-document/` still existed on disk, and checking `hermes skills list` showed it was **actively registered and enabled** (`local` source, `enabled` status), not just orphaned files.

The repo-tracked copy (`skills/document-graph/write-document/`) had been deleted earlier when the code-execution approach was rejected in favor of the MCP server. What was missed: the copy that had been `docker cp`'d into the running container's `hermes-data/` volume was never removed, so it remained live and discoverable by any persona even after the repo-level decision to abandon it.

## Decision

Removed the stale skill from the running container:
- `hermes skills uninstall write-document` didn't apply (not hub-installed — "may be a builtin" error), so removed the directory directly: `rm -rf /opt/data/skills/document-graph/write-document` (plus the now-empty parent folder).
- Verified via `hermes skills list` that it no longer appears.
- Confirmed no lingering Neon credential in `hermes-data/.env` (it was never written there in the current design — only briefly during the earlier discarded approach, and already cleaned up in the document-graph-mcp-server note).

## Rationale

Deleting the repo-tracked source of a discarded design isn't sufficient when that design was already deployed into a running system — the running container's own state (here, `hermes-data/`, which is gitignored and not visible in `git status`) needs its own explicit cleanup pass. This is a real gap in the workflow so far: "delete from the repo" and "delete from the live container" are two different actions, and only doing the first can leave a rejected, unsafe capability silently active.

## Impact

- No agent could have actually reached the raw Neon credential via this path in practice (it required the skill being invoked, and no persona referenced it after the pivot to MCP), but it was a live, discoverable capability during the gap between deciding to abandon it and this cleanup — worth being precise that the risk was latent, not exploited.
- Establishes a checklist item: whenever a persona, skill, or config file is deleted/replaced in the repo, explicitly check whether a copy also needs removing from `hermes-data/` (or any other gitignored runtime state), since `git status` won't surface it.

## Follow-Ups

- No other known stale artifacts as of this note — but worth a periodic `hermes skills list` / `hermes-data/` audit whenever a persona or tool design is abandoned mid-stream, not just when it's cleanly finished.
