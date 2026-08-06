# CLAUDE.md

This file provides guidance to Claude Code (or any agent) working in this repository.

## Project Overview

Horology is a solo founder's personal "AI co-founder" system: **Second-Soul**, a supervisor agent, dispatches work to named specialist subagents (GTM strategy, marketing content, codebase/security monitoring, and more over time). The founder talks only to Second-Soul.

Framework, in one line: Hermes Agent (Nous Research) as the agent runtime, subagents as Hermes **profiles** dispatched via **kanban tasks**, purpose-built MCP servers (no arbitrary API/SQL access) for anything external. Full architecture, diagrams, and current subagent roster: [`docs/architecture/system_overview.md`](docs/architecture/system_overview.md) — that's the file to read for how the system actually works. This file is about how the *repo's own documentation* is organized, not the system itself.

## Where Repo Documentation Goes

Four kinds of doc, four folders — matching content to the right one is what keeps this navigable as it grows:

| Folder | What goes here | Written for |
|---|---|---|
| `docs/planning/research/` | Open questions being investigated: options considered, tradeoffs, sources. No decision yet, or the investigation phase of one. | Future you/agent asking "why did we consider X" |
| `docs/planning/notes/` | Decisions actually made and implemented: what changed, why, verified how. | Future you/agent asking "what did we do and why" |
| `docs/architecture/` | Standing, current-state reference — updated in place, not dated. How the system works *right now*. | Anyone orienting themselves in the system before making a change |
| `docs/runbook/` | Practical how-to: commands to run, in what order, with what flags. Terminal-ready. | You, running something yourself; an agent needing the exact CLI invocation |

**The rule for research vs. notes**: if there's a genuine "we looked into several options before deciding" phase, write it up as a `research/` brief first (`docs/planning/templates/RESEARCH_BRIEF_TEMPLATE.md`), then a short `notes/` entry for the decision that references it. If it was direct — found a problem, fixed it, verified — a single `notes/` entry is enough (`docs/planning/templates/IMPLEMENTATION_NOTE_TEMPLATE.md`). Don't merge a real investigation into a decision note; don't split a two-line fix into two files either.

**The rule for architecture vs. notes**: architecture describes the system as it is today, always current, no history. Notes describe a specific change, dated, never rewritten. When architecture changes, update `docs/architecture/` in place *and* leave the notes/research trail explaining why, in `docs/planning/`.

**The rule for runbook**: pure instruction — a human or agent should be able to copy-paste a command block from here and have it work, without needing to read a note first. If a runbook doc needs to explain *why* something is done a certain way (not just *how*), that explanation is a one- or two-line pointer to the relevant note, not inlined.

See `docs/planning/README.md` for the full workflow and naming convention.

## How Subagents Should Create Documents

This is a separate thing from the repo docs above — this is about the **business documents subagents produce while running** (GTM recommendations, marketing copy, findings), stored in Postgres via the document-graph MCP server, not as files in this repo.

Any subagent (or Second-Soul itself) that produces a **finished, substantive output** — not ordinary conversation or intermediate reasoning — should write it via the `write_document` MCP tool. The rule for what counts: something a founder or another agent might want to find, reference, or build on months later.

**`doc_type` must be one of:**
- `recommendation` — "here's what I think we should do and why."
- `content` — usable output artifacts: copy, drafts, written material.
- `analysis` — findings/observations without an explicit recommendation attached.
- `report` — a status/summary rollup, typically time-boxed.

**Conventions, enforced in every subagent persona:**
- Write the **full** answer as `content` — assume it's read standalone.
- Set `created_by_agent` to the profile name.
- Use `supersedes_id` when a document replaces an earlier one's conclusion; `link_documents` (with a `relation` like `related_to`/`informed_by`/`contradicts`) when two documents are connected but neither replaces the other.
- A kanban task must still call `kanban_complete`/`kanban_block` after writing a document — the two systems are separate. Keep the kanban summary brief (a pointer to the document id/title), not a duplicate of the content.

## Working in This Repo — Quick Notes

- **Personas are edited in `personas/`, then synced into the running container** (`hermes-data/` is gitignored runtime state, not the source of truth). Sync commands: [`docs/runbook/docker/hermes_setup.md`](docs/runbook/docker/hermes_setup.md).
- **Before editing `config.yaml` on disk**: don't, while Hermes is running — the live process reverts direct file edits. Use `hermes config set` or equivalent CLI commands.
- **Verify claims hands-on before designing around them.** Documentation (including Hermes's own) has been wrong or stale more than once this project — prefer a real test over trusting docs when the design will depend on the answer.
