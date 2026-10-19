# Subscription agents: source, naming, skills and prompts

## Topic
- subscription-agents-setup

## Context

Welladino already ran proposals and decisions through Sheets and Drive, used subscription agents for investigation and planning, and showed work in ClickUp through Apps Script. The Apps Script modules were copied by hand, so changes were hard to track, and the agents' skills and prompts lived outside version control.

## Decisions

**Apps Script under version control (2026-10-10).** The ClickUp sync became local source, tested offline and published with clasp after a source review and live preview. With clasp 3.1.0 and a refreshed Google login, a read-only clone imported all 14 live files on 2026-10-10. Credentials and the local `.clasp.json` target stay out of Git. Publishing changes code that existing triggers will run, so every publish needs review.

**Name: subscription agents (2026-10-10).** The folder was first `managed-agents/`; it became `subscription-agents/` to make the cost model clear: these agents run on existing platform subscriptions. The Drive overview became "Subscription agents — Framework Overview". The sync runs selected rows one at a time under a script lock; it moves records and can mark rows Ready, but never launches an AI worker. Hermes kanban is a separate system, not a Pipeline runner.

**Development reset (2026-10-10).** With the founder's authorisation, test records were removed: the EPIC-NEWS-33 item, its pilot decision, two Drive outputs, test references, the Curation page addition and framework Pipeline IDs 39–42. Ten standing guide, register and template entries were removed from the Document Index without deleting the files. IDs were compacted, leaving 36 Pipeline items, 2 decisions and 15 indexed documents; routine work never renumbers. The Horology domain was added to the dropdowns and filtered views, and its ClickUp list (`901820246905`) was published through clasp with writes disabled. All 17 offline sync tests passed.

**Skills and prompts in the repository (2026-10-10 to 10-12).** The three Welladino skills (capture and triage, research, technical assessment) moved into the repository, and the Research and Technical Assessment prompts from Agent Register Master IDs 1 and 2 were copied exactly into `personas/subscriptions/`, separate from Hermes' `personas/subagents/`. The register's Master column now holds repository paths; clickable GitHub links wait for publication. A `horology-mcp-access` skill was added to the private Horology plugin (release `pluginrel_6accb189d62c819193ed45f45f6ab880`, version 1.0.1) without changing its App identity or connection; validators passed and `gateway_status` worked through it.

**Repository layout (2026-10-12).** Skills moved into `plugins/welladino-workflows/skills/` beside the plugin manifests and icon, the Apps Script root became `google_appscript/`, and gateway tests were gathered under the root `tests/` tree. On 2026-10-15 the plugin folders were renamed `plugins/horology-workflows/` and `plugins/horology-tools/`.

## Rationale

Version control, offline tests and a preview step make changes to live Sheets, ClickUp and agent instructions reviewable, which hand-copying never was.

## Impact

- Current design: [subscription-agent architecture](../../architecture/subscription-agents/subscription-agents.md). Maintenance: [runbook](../../runbook/subscription-agents/README.md).

## Follow-Ups

- Add clickable GitHub links to the Agent Register's prompt sources once published.
- No scheduler or concurrent-writer coordination exists; one writer at a time until ID allocation and work claiming are coordinated.
- Automatic skill loading in a refreshed ChatGPT or Codex host has not been tested behaviourally.
