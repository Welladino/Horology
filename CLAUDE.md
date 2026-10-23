# Repository guidance

Horology is a personal or small trusted-group agent operating system. Its main workflow uses Claude, ChatGPT or Codex subscriptions with versioned skills, Google Sheets as the visible workflow record, Drive for source material and deliverables, Apps Script for a lightweight UI, and restricted MCP services backed by Neon. Hermes is an optional local runtime with one default agent; do not reintroduce the retired profile/kanban design.

Read [the architecture overview](docs/architecture/overview.md) before changing system behavior and [workspace records](docs/architecture/subscription-agents/workspace-records.md) before changing workbook logic.

## Where documentation belongs

| Location | Content |
| --- | --- |
| `README.md` | Short public introduction and navigation |
| `docs/architecture/` | Current behavior and boundaries, updated in place |
| `docs/runbook/` | Copy-paste-ready setup, operation and recovery |
| `docs/planning/research/` | Dated investigation, options and tradeoffs |
| `docs/planning/notes/` | Dated decisions and implementation evidence |

Keep component documentation in `docs/`, not beside source code. A component can use module docstrings and comments for code-level behavior, but its setup and operating guide belongs in the runbook. Historical planning files may describe old behavior; standing architecture and runbooks must not.

For an investigated decision, write a research brief first and a short implementation note when the choice is made. For a direct fix, one implementation note is enough. Templates and naming rules are in [planning documents](docs/planning/planning_documents.md).

Runbooks should state purpose, prerequisites, exact commands, expected result, how to stop or recover, and any destructive-data warning. Prefer verification commands over dated claims.

## Workspace privacy

Do not add a person's live Google Sheet, Drive folder, Apps Script web-app URL, email, OAuth credential or other private identifier to public documentation or a distributable skill. Use placeholders and explain how a user finds the value in their own workspace.

The Pipeline's **Locations** tab defines each user's Drive structure. Never hard-code the founder's folder names as required schema. Agents follow the Location URLs and folder types recorded there.

## Skills and releases

Skill source lives under:

- `plugins/horology-workflows/skills/`;
- `plugins/horology-specialists/skills/`;
- the MCP-access and document-graph plugin skill folders.

Installed plugins and uploaded archives are distributions, not source. When workflow state changes, update the canonical `workflow.yaml`, affected skills, tests and standing diagrams together. Supporting files such as `references/workflow.yaml` must remain inside every package that needs them.

Subscription-agent business outputs go to the user's Drive and registers. The supervisor records run claims and outcomes through the document graph. A Stage 3 specialist deliverable is followed by Stage 4 synthesis in the same run before founder review.

## Working safely

- Keep secrets in Secret Manager or ignored private environment files. Root `.env` is not a common bucket for service credentials.
- Do not give an agent arbitrary SQL or provider access when a fixed, bounded MCP tool can express the operation.
- Do not expose local MCP ports beyond `127.0.0.1`.
- Do not edit `hermes-data/config.yaml` while Hermes is running; use the Hermes CLI because the process may overwrite direct edits.
- Treat native Drive, GitHub and other platform connectors as separate permission boundaries; gateway policy does not constrain them.
- Preserve permanent Pipeline, Decision and Document IDs. Do not infer identity from row position or title.
- Verify external-integration claims hands-on before documenting them as current.

## Verification

Run the proportionate checks for the change. The complete guide is [tests and audits](docs/runbook/testing/running_tests_and_audits.md).

```bash
.venv/bin/python -m pytest tests/unit -q
```

Changes to MCP services or Compose should also run the relevant integration/system checks and security audit. Tests are organized as unit (no external component), integration (disposable PostgreSQL or local HTTP), system (real Compose stack), and manual smoke helpers. Put new tests in the matching folder and keep test filenames unique across the tree.
