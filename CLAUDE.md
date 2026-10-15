# CLAUDE.md

This file provides guidance to Claude Code (or any agent) working in this repository.

## Project Overview

Horology is a solo founder's personal "AI co-founder" system: **Second-Soul**, a supervisor agent, dispatches work to named specialist subagents (GTM strategy, marketing content, codebase/security monitoring, and more over time). The founder talks only to Second-Soul.

Framework, in one line: Hermes Agent (Nous Research) as the agent runtime, subagents as Hermes **profiles** dispatched via **kanban tasks**, purpose-built MCP servers (no arbitrary API/SQL access) for anything external. Full architecture, diagrams and the current subagent roster start at [`docs/architecture/README.md`](docs/architecture/README.md) — read that for how the system actually works. This file is about how the *repo's own documentation* is organized, not the system itself.

## Where Repo Documentation Goes

Four kinds of doc, four folders — matching content to the right one is what keeps this navigable as it grows:

| Folder | What goes here | Written for |
|---|---|---|
| `docs/planning/research/` | Open questions being investigated: options considered, tradeoffs, sources. No decision yet, or the investigation phase of one. | Future you/agent asking "why did we consider X" |
| `docs/planning/notes/` | Decisions actually made and implemented: what changed, why, verified how. | Future you/agent asking "what did we do and why" |
| `docs/architecture/` | Standing, current-state reference — updated in place, not dated. How the system works *right now*. One subfolder per area; diagrams in `diagrams/`, rendered with `scripts/docs/render_diagrams.py`. | Anyone orienting themselves in the system before making a change |
| `docs/runbook/` | Practical how-to: commands to run, in what order, with what flags. Terminal-ready. | You, running something yourself; an agent needing the exact CLI invocation |

**The rule for research vs. notes**: if there's a genuine "we looked into several options before deciding" phase, write it up as a `research/` brief first (`docs/planning/templates/RESEARCH_BRIEF_TEMPLATE.md`), then a short `notes/` entry for the decision that references it. If it was direct — found a problem, fixed it, verified — a single `notes/` entry is enough (`docs/planning/templates/IMPLEMENTATION_NOTE_TEMPLATE.md`). Don't merge a real investigation into a decision note; don't split a two-line fix into two files either.

**The rule for architecture vs. notes**: architecture describes the system as it is today, always current, no history. Notes describe a specific change, dated, never rewritten. When architecture changes, update `docs/architecture/` in place *and* leave the notes/research trail explaining why, in `docs/planning/`.

**The rule for runbook**: pure instruction — a human or agent should be able to copy-paste a command block from here and have it work, without needing to read a note first. If a runbook doc needs to explain *why* something is done a certain way (not just *how*), that explanation is a one- or two-line pointer to the relevant note, not inlined.

See `docs/planning/README.md` for the full workflow and naming convention.

## Subscription agents

The secondary subscription-agent workflow uses personal AI subscriptions, Drive instructions and Sheets records. Read [its architecture](docs/architecture/subscription-agents/README.md) and [runbook](docs/runbook/subscription-agents/README.md) before changing it. Its skill source is `plugins/horology-workflows/skills/`; installed copies are distributions. Subscription-agent business outputs go to Drive/Sheets. The Neon and kanban rules below apply to Hermes/Second-Soul agents, not subscription-agent sessions.

## How Hermes Subagents Should Create Documents

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
- Use `supersedes_id` when a document replaces an earlier one's conclusion; `link_documents` (with a `relation` like `informed_by`/`contradicts`) for a specific relationship you know, distinct from generic similarity.
- **Call `auto_link_similar_documents` with the new document's id immediately after every `write_document`** — this embeds the document and auto-creates `related_to` links to any existing document above a similarity threshold, catching related documents that share almost no vocabulary (which `link_documents` called manually would likely miss). This is the default linking mechanism now, not optional.
- **Check the similarity scores `auto_link_similar_documents` returns in `newly_linked`.** A score at or above **0.90** means near-duplicate, not just related — say so explicitly in your `kanban_complete` summary (e.g. "near-duplicate of doc #41, written 2026-08-06") instead of letting it read as an ordinary `related_to` link. This matters most for anything written on a recurring schedule (e.g. a daily status report), where template structure alone can push scores high even when the substance hasn't meaningfully changed — the founder should be able to tell "this is genuinely new" from "this is mostly the same as last time" without opening both documents. Don't skip writing the document because of a high score — the founder decides whether a near-duplicate was worth writing, you don't decide that by suppressing it. (Threshold tuned from an initial 0.95 to 0.90 on 2026-08-07 after the first real recurring case — two `code-sentinel` reports on a dormant repo — scored 0.9343, clearly a near-duplicate in substance but below the original bar. See `docs/planning/notes/2026-08-06_document-graph-v1_note.md`.)
- A kanban task must still call `kanban_complete`/`kanban_block` after writing a document — the two systems are separate. Keep the kanban summary brief (a pointer to the document id/title), not a duplicate of the content.

## Working in This Repo — Quick Notes

- **Personas are edited in `personas/`, then synced into the running container** (`hermes-data/` is gitignored runtime state, not the source of truth). Sync commands: [`docs/runbook/docker/hermes_setup.md`](docs/runbook/docker/hermes_setup.md).
- **Before editing `config.yaml` on disk**: don't, while Hermes is running — the live process reverts direct file edits. Use `hermes config set` or equivalent CLI commands.
- **Verify claims hands-on before designing around them.** Documentation (including Hermes's own) has been wrong or stale more than once this project — prefer a real test over trusting docs when the design will depend on the answer.
- **Run `python3 -m pytest tests/ -v` before shipping a change to either MCP server or `docker-compose.yml`**, and `pip-audit` (dev venv + each server's own `requirements.txt`) periodically. See [`docs/runbook/testing/running_tests_and_audits.md`](docs/runbook/testing/running_tests_and_audits.md). Three kinds, by folder: `tests/unit/` (no database or Docker), `tests/integration/` (a disposable migrated Postgres; skipped without it) and `tests/system/` (the real Docker Compose stack; skipped without Docker). Where a new test goes: [`tests/README.md`](tests/README.md). Neither replaces hands-on verification against the real system for anything touching a genuinely new external integration point.
