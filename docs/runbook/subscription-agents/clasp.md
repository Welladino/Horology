# Apps Script projects: setup and publishing

Two projects, each in its own folder under `google_appscript/`; what they do is in the [Apps Script architecture](https://github.com/Welladino/Horology/blob/main/docs/architecture/subscription-agents/apps-script.md). Run each project's commands from its folder.

| Project | Folder | Script ID | Attached to |
|---|---|---|---|
| [Horology — Pipeline decisions](https://script.google.com/d/16wWrpPS5GnmZck7ZSKXPV61by7_Vy8vXjAj-ddSAt5N7pDtMnxv5m5Iy/edit) | `pipeline-decisions/` | `16wWrpPS5GnmZck7ZSKXPV61by7_Vy8vXjAj-ddSAt5N7pDtMnxv5m5Iy` | Pipeline workbook |
| [Horology — ClickUp Sync](https://script.google.com/d/1SHh-DazeGYhF5LrHl1m5itQTqYblyQ6k8HmiVRekSMgYR0VjY1Ks6pyG/edit) | `clickup-sync/` | `1SHh-DazeGYhF5LrHl1m5itQTqYblyQ6k8HmiVRekSMgYR0VjY1Ks6pyG` | Standalone |

## Set up clasp

Each project pins clasp 3.4.1. Install it globally too:

```sh
npm install -g @google/clasp@3.4.1
```

Enable the Apps Script API at [Apps Script settings](https://script.google.com/home/usersettings), then sign in:

```sh
clasp login
clasp show-authorized-user
```

Without a local browser callback, use `clasp login --no-localhost`. Credentials stay in clasp's own store, never in the repo.

## Connect a project

Each folder needs a `.clasp.json` (ignored by Git). Copy the template and put in the script ID from the table:

```sh
cp .clasp.example.json .clasp.json
clasp status
```

Keep `"rootDir": "src"`. Status lists the files that would upload: only `src/` modules, `.html` files and `appsscript.json`.

## Publish a change

For `pipeline-decisions`, build the UI fragment first and use the package script to push it:

```sh
npm run ui:build
npm test
npm run clasp:push
```

The UI source is `google_appscript/shared-ui/`; its generated `src/SharedUi.html` must be current. `npm test` checks this. For `clickup-sync`, which has no HTML fragment, use the ordinary commands below.

```sh
npm test
git diff -- src
clasp push
```

Push replaces the project's files with `src/`, including deleting files that aren't there; triggers pick up the new code straight away. Then run the project's preview in the live project (below).

If someone edited in the browser, compare before pushing:

```sh
compare_dir="$(mktemp -d)"
cp .clasp.json "$compare_dir/"
(cd "$compare_dir" && clasp pull)
diff -ru src "$compare_dir/src"
```

`diff` exits 1 when files differ. Merge what you want to keep into `src/`, rerun the tests, then push.

## Pipeline decisions

Bound to the Pipeline workbook. **Extensions → Horology — Pipeline decisions → Open Horology workspace** opens the private web app. The founder removed its time trigger; web decisions apply immediately, while the edit trigger can process direct human edits if still installed. Apps Script/API writers must call `applyDecisions` explicitly. `installTriggers` would recreate both the edit and time triggers, so do not run it unless that behavior is wanted.

## Locations

The folder path browser and **Check Drive & update Locations** action are in the Horology web workspace’s **Folders** view. The web app may ask the owner to authorize read-only Drive access.

## ClickUp Sync

Standalone. In the project's **Project Settings → Script Properties**:

| Property | Value |
|---|---|
| `CLICKUP_TOKEN` | Your personal ClickUp API token (ClickUp settings → Apps). Type it here only. |
| `PIPELINE_SHEET_ID` | The Pipeline workbook ID: `1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI` |

Map an existing task by placing its full `https://app.clickup.com/t/...` URL in that Pipeline row's **ClickUp Pipeline URL** cell. AI can suggest a match, but confirm the task before saving its URL. Unlinked rows are ignored; this script does not create tasks.

Then, in the editor:

1. `previewSync`: inspect the linked task IDs and proposed status changes in the Execution log. Writes nothing.
2. `applySync` once to align status and establish the baseline. It does not repost historical decisions or documents.
3. Make a small test change to a linked Pipeline row or its indexed documents, run `previewSync`, then `applySync`. Check that one comment appears and that repeating the run posts nothing.
4. Keep the existing hourly `applySync` trigger. If it is missing, `installHourlyTrigger` creates one; it leaves an existing trigger alone. `stopSync` removes it.

To pause: `stopSync`, or `ENABLE_WRITES: false` in `src/Config.js` and push.

The previous `LIST_<Domain>` Script Properties are ignored. They may be removed after the new version is verified.

## Troubleshooting

| Symptom | Check |
|---|---|
| Login expired or wrong account | `clasp login`, then `clasp show-authorized-user` |
| Script unavailable | The script ID, and the account's access to the project |
| Apps Script API disabled | Enable it in account settings and retry |
| Unexpected upload files | `.clasp.json` rootDir, `.claspignore`, `clasp status` |
| A menu is missing in the workbook | Reload the workbook; the menus are added when it opens |
| "Registers tab needs exactly one row matching…" | The Registers tab has one row named like the register, with a Google Sheets link |
| ClickUp item blocked "Task link conflicts with existing sync state" | Confirm the Pipeline URL, then reconcile the old task ID in `_ClickUp Sync` |
| ClickUp item blocked "Uncertain previous ClickUp write" | Inspect ClickUp for the comment before clearing the pending state; avoid duplicates |
| Remote edits differ | Compare as above before pushing |

Runtime errors are in each project's **Executions** view. `clasp run` needs extra API setup and isn't used here.
