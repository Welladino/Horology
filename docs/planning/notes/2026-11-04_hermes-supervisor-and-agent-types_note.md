# Hermes supervisor and Agent types

Pipeline item 72. The Hermes runtime already had Coordinator, Operator and
Explorer profiles, but its bootstrap removed `horology-supervisor`; Coordinator
carried a partial workflow copy, and the canonical workflow, web app and run
claim service did not treat Hermes and ChatGPT Work as executable Agent types.

## Implementation

- Added `scripts/ops/hermes/horology_supervisor_dispatch.md`. Coordinator runs
  dispatch and status without claiming, creates one initial Operator Kanban
  task per Ready Hermes item, and chains Explorer code work and the Operator
  continuation with `parents`. Operator claims as Hermes/Local and owns the
  workspace records and `finish_run`.
- Changed the existing bootstrap's skill section only: every destination is
  cleared before copy, Coordinator and Operator both receive the shared
  supervisor core, and the Hermes adapter is copied to
  `references/dispatch.md`. The Coordinator skill now contains only
  Hermes-specific routing, permission and approval rules.
- Added Hermes and ChatGPT Work to `workflow.yaml`, record guidance and the web
  app. ChatGPT Work is Cloud only and claimed by Codex; Hermes is Local only
  and claimed as Hermes by Operator. Manual and Unassigned remain ineligible
  for Ready.
- Allowed Hermes in document-graph `claim_item`, with a Local-only validation.
  Coordinator's tracked document-graph connection now exposes only read-only
  search and history tools needed by supervisor status mode.
- Updated standing architecture, setup and operating documentation. The Codex
  workflows plugin version is 0.6.16.

## Verification

- Focused workflow, skill packaging and document-graph tests pass.
- The Pipeline decisions Apps Script test suite passes, including add/edit
  location rules and decision transitions for Hermes and ChatGPT Work.
- The full unit suite is run before delivery and recorded in the implementation
  report.

## Founder delivery steps

1. Review and merge the pull request; do not deploy from this branch directly.
2. Rebuild and upload the changed Claude supervisor/capture skills and the
   Codex workflows plugin.
3. Rerun `./scripts/ops/hermes/bootstrap.sh` to refresh the persistent skill
   folders and tracked Coordinator configuration.
4. Complete Coordinator's document-graph OAuth login and verify status mode.
5. Provide Explorer's scoped GitHub hook, then run one implementation-route
   Hermes item end to end. No credential is committed by this change.

