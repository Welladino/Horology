# ClickUp sync for subscription agents

## Current state

Connected to the existing Welladino — ClickUp Sync project through clasp.
The live project was downloaded on 10 October 2026 after refreshing clasp login.
All 14 files, including founder-entered settings, the list-discovery utility and
manifest, are preserved locally. These imported files are the maintained source.
No upload, trigger or online configuration change was performed.

## Layout

- `src/`: Apps Script modules. The live `appsscript.json` manifest will be pulled.
- `tests/`: offline tests; no Google or ClickUp calls.
- `WORKFLOW.md`: schema, stages, status mapping and operational instructions.
- `package.json`: local CLI and test commands.
- `.clasp.example.json`: connection template; copy to .clasp.json after verifying the target.
- `.clasp.json`: local target connection, ignored by Git until explicitly shared.

## Local development

Run from this directory:

```sh
npm install
npm test
```

The installed CLI is clasp 3.1.0. Credentials belong in clasp's user login store,
not this repository. ClickUp's token remains in Apps Script Script Properties.

The local .clasp.json already points to the verified existing project and uses
src as its rootDir. Login uses your own account; credentials are outside Git.
The downloaded JavaScript modules use .js filenames, matching clasp's export.
Do not also create .gs copies of the same modules.

Once connected:

```sh
npm run clasp:status
npm test
```

Inspect `git diff` before `npm run clasp:push`. Push replaces the online project's
files. Do not use watch or force for routine updates. Run previewSync in Apps
Script after publishing; source upload does not itself validate live behaviour.
Existing time triggers can use updated code, so pause writes during rollout.

If someone edits in the browser, pull into a temporary directory and compare
before replacing tracked files. Avoid blind pull/push against local changes.
Only source and manifest in src are published; README and tests stay local.

The live source was imported through clasp. No upload, trigger or deployment
was performed during setup.

## Verification on 10 October 2026

A read-only clasp clone succeeded after refreshing the Google login. The live
source includes testClickUpConnection and the Clickuplist discovery utility,
in addition to the sync modules. Offline tests isolate deployment-specific
configuration so running tests never uses credentials or modifies the project.

For step-by-step authentication, project connection, comparison and publishing, see the [clasp runbook](../../docs/runbook/subscription-agents/clasp.md).
