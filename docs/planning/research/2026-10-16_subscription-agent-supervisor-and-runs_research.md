# Subscription-agent supervisor, runs and scheduled oversight

## Topic
- subscription-agent-supervisor-and-runs

## Question
- How should Pipeline items get from Ready to a finished deliverable: who chooses the specialists, how runs start, where they run, how several items are handled at once, and what runs on a schedule?

## Summary
- Runs are **started by the founder from a session**: in Claude Code or Codex, "run the Ready items" (or "run item 42"). There is no automatic trigger, dispatcher script or server.
- The `horology-supervisor` skill has two modes. **Dispatch** finds Ready rows for its own platform, claims them in a new Runs tab and starts **one session per item**, locally or in the cloud according to a new Pipeline **Run location** column. **Item** mode handles exactly one item: it chooses specialists, runs them as subagents, checks the results and saves.
- Schedules do **oversight, not work**: a daily **Digest** Google Doc (report card, findings, what's waiting, health checks) and later a **Planner** that acts only on rows set to `Agent status = Plan`.

## Sources
- Claude Code routines and their API trigger: <https://code.claude.com/docs/en/routines>
- Cloud sessions, `claude --cloud`, credentials outside the VM: <https://code.claude.com/docs/en/claude-code-on-the-web>
- Cloud environments and network secrets (never sent to `api.anthropic.com`): <https://code.claude.com/docs/en/cloud-environments>
- Projects (coordinator conversation with cloud threads, public beta): <https://code.claude.com/docs/en/claude-projects>
- Agent teams (experimental, interactive only): <https://code.claude.com/docs/en/agent-teams>
- Codex subagents and custom agents: <https://developers.openai.com/codex/subagents>
- Codex plugins (skills, MCP, hooks; no agents): <https://learn.chatgpt.com/docs/plugins>, <https://developers.openai.com/plugins/build/plugins>
- Codex cloud scripting gap: <https://github.com/openai/codex/issues/24777>; Codex GitHub Action (API key only): <https://learn.chatgpt.com/docs/github-action>
- Paperclip (open-source agent control plane): <https://github.com/paperclipai/paperclip>
- Live registers read on 2026-10-15: 37 Pipeline items (none Ready or scoped), 2 draft agents, empty Decision Register.

## Findings

**Is a supervisor worth it?** With two specialists, routing was a rule. With six (research, technical assessment, security review, GTM, marketing strategy, content planner) and items that can need more than one, a supervisor that reads the item and the skills earns its place. Agents and skills scale best as **skills**: the platform already lists installed skills' names and descriptions, and the supervisor opens a `SKILL.md` only for the 2–3 candidates. The Agent Register becomes an overview, not an input.

**Packaging.** Codex plugins can't ship agents (checked docs and installed manifests), and Claude plugins can. Personas are therefore skills in two plugins: `horology-workflows` (supervisor, capture and triage, later planner and digest) and `horology-specialists`. The same `SKILL.md` files load in Claude, Codex and Hermes (tested on Hermes v0.20.0).

**Harness limits that shaped the design.**
- Subagents can't start subagents (Claude Code; Codex defaults to one level). One supervisor session working through many items would also mix their results. So **each item gets its own session** whose supervisor is the only orchestrator, and specialists are its subagents.
- A session started with bash (`claude -p`, `claude --cloud`, `codex exec`, `codex cloud exec`) is a full top-level session with its own subagents. This works from the founder's Mac, where the CLIs are signed in.
- Inside a cloud session or routine, the `claude` CLI has no claude.ai sign-in (credentials stay outside the VM), so a cloud session can't start further sessions with bash. Firing another routine's `/fire` endpoint with `curl` is possible in principle, but needs the token in a plain environment variable (network secrets are never attached to `api.anthropic.com`), shell access to that host is unconfirmed, and results come back only through records. Judged too complex.

**Triggers considered and set aside.**
| Option | Why not now |
|---|---|
| Apps Script watcher → Claude routine `/fire` per item | Works for Claude and costs nothing when idle, but Codex has no equivalent endpoint; the founder prefers to start runs by hand |
| Local dispatcher script (with or without launchd) | Not needed once a session can dispatch with bash |
| Scheduled supervisor running work | Costs a session even when nothing is Ready |
| CLI in a cloud VM or container | Extra infrastructure and a login to keep alive; revisit if unattended Codex runs are needed |
| GitHub Actions (Codex) or `@codex` mentions | Per-token API billing, or results that land in GitHub |
| Paperclip | Strong ideas (atomic checkout, approvals, budgets) but needs its own server and moves tracking out of Sheets |
| Claude Projects | Native coordinator with cloud threads; in beta and conversational, kept as an option |
| Lead agents per area, or fixed chained steps | More to maintain; one item-scoped supervisor plus skills covers it for now |

**Email and notifications.** Connector sending isn't dependable for unattended jobs (Claude's Gmail connector is documented as drafts-only, newer reports say send with approval; ChatGPT can send, with limits). Any scheduled email or Slack post should be sent by code (Apps Script or the GCP API), not by an agent. Slack is deferred.

## Recommendation

**Pipeline (Master tab).**
- **Agent type:** Claude Code, Codex, Manual, Unassigned. Cowork and ChatGPT Work may return later if they can be started from bash.
- **Agent status:** No action, **Plan**, Ready. Plan asks the Planner to scope or split the item.
- **Run location** (new): Local or Cloud, chosen by the founder per item.
- **Planner output** (new): a Yes/No dropdown; Yes when the Planner has written a sharper question or steps for the row.

**Runs tab (new, Pipeline workbook).** One row per run: Run ID, Pipeline ID, Agent type, Run location, Status (claimed, running, done, failed, released), Claimed at, Claim expires (2 hours), Session link, Skills used, Plan reason, Output document IDs, Notes, Started, Finished. It records what actually happened; later it can be copied into Neon `run_log`.

**Steps tab (new, Pipeline workbook).** Written by the Planner when an item needs splitting: Step ID, Pipeline ID, Order, Step / question, Suggested specialist, Status, Output document IDs, Created by run. The Pipeline row stays the single item; when it's Ready, its session works through the steps in order, choosing the specialist for each.

**Supervisor (`horology-supervisor`).**
- **Dispatch mode**, started by the founder: read Ready rows where Agent type matches this platform; claim each in Runs; start one session per item by Run location:

  | Agent type | Local | Cloud |
  |---|---|---|
  | Claude Code | `claude -p "…"` | `claude --cloud "…"` |
  | Codex | `codex exec "…"` | `codex cloud exec "…"` |

  Without bash (for example claude.ai chat), run items one at a time as subagents.
- **Item mode**: one item only. Read the row, decisions, Steps (if any) and the document graph; choose specialists; run them as subagents; check; save to Drive, the Document Index and a proposed decision; set Awaiting decision; close the Runs row.

**Scheduled oversight.**
- **Digest** (daily, any platform's scheduler): a free-form Google Doc report card. Base content: counts by status (report card), what finished yesterday with key findings, recommendations and links, what's waiting on the founder, and health and graph checks (stale claims, items stuck awaiting decision, outputs missing from the Index, near-duplicates, sync errors). The agent chooses tables or diagrams; charts and diagrams go in as images. Registered in the Document Index with Graph Inclusion FALSE. It also lists rows that look too big ("set Plan if you agree").
- **Planner** (later): only `Agent status = Plan` rows. A sharper question rewrites Next step (old wording kept in Runs); a split writes Steps. Then Planner output = Yes and Agent status = No action.
- **Watchers** (later): defined by the founder.

**Build order.**
1. Pipeline columns and values, Runs and Steps tabs.
2. Supervisor dispatch and item modes; record rules in the skills.
3. Digest skill and Google Doc template.
4. Planner; then watchers.

## Open Questions
- Do `claude -p` and `codex exec` started by a session load the synced plugins and the Google-signed-in connectors without prompting, and which permission mode lets unattended child sessions use them?
- Do `claude --cloud` sessions see the skills (committed under `.claude/skills/`) and the claude.ai connectors (document graph re-added as a claude.ai connector)?
- Does `codex cloud exec` work with a published Codex cloud environment (it's experimental and needs an environment ID)?
- How many child sessions to run at once without hitting subscription limits.
- Whether the ClickUp sync should show Run location, Plan and Planner output (it doesn't validate those values today, and only treats `Manual` specially).
