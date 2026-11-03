# Apps Script projects: setup and publishing

Two projects, each in its own folder under `google_appscript/`; what they do is in the [Apps Script architecture](https://github.com/Welladino/Horology/blob/main/docs/architecture/subscription-agents/apps-script.md). Run each project's commands from its folder.

| Project | Folder | Attached to |
|---|---|---|
| Horology — Pipeline decisions | `pipeline-decisions/` | The user's Pipeline workbook |
| Horology — ClickUp Sync | `clickup-sync/` | A standalone private Apps Script project |

## Set up clasp

Node.js, npm and clasp are general development tools, so the normal Horology setup installs them once for the user rather than once per Apps Script project. Node.js 22 includes npm.

Check the existing installation first:

```sh
node --version
npm --version
clasp --version
```

If Node.js or npm is missing, install Node.js 22 with the user's normal system or Node version manager. If clasp is missing or is not version 3.4.1, install the pinned version globally so it remains available to other projects:

```sh
npm install -g @google/clasp@3.4.1
```

Then change to the Apps Script project before signing in or running project commands:

```sh
cd google_appscript/pipeline-decisions
```

Enable the Apps Script API at [Apps Script settings](https://script.google.com/home/usersettings), then sign in:

```sh
clasp login
clasp show-authorized-user
```

Without a local browser callback, use `clasp login --no-localhost`. Credentials stay in clasp's own store, never in the repo.

For ClickUp Sync, change projects before running its commands:

```sh
cd ../clickup-sync
clasp show-authorized-user
```

If you opened a new terminal, start at the repository root and use `cd google_appscript/clickup-sync`. The login is shared by clasp, but `.clasp.json`, package scripts and upload roots are project-specific.

### Optional: keep clasp inside each project

Both Apps Script `package.json` files pin clasp 3.4.1. A user who prefers project-local tools can install that dependency inside each project instead of installing clasp globally:

```sh
cd google_appscript/pipeline-decisions
npm install --no-package-lock
npx clasp login
npx clasp show-authorized-user
```

`node_modules/` is ignored by Git. The `--no-package-lock` option avoids creating a new lockfile in this repository. When clasp is installed locally, `npm run clasp:status` and `npm run clasp:push` automatically use that local copy. Repeat the local install inside `google_appscript/clickup-sync/` if that project should also be self-contained.

The remaining examples use the globally available `clasp` command. With a project-local installation, replace it with `npx clasp` or use the matching npm script.

## Connect a project

Each folder needs a `.clasp.json` (ignored by Git). Copy the template only when the file doesn't exist yet, then replace the placeholder with the Script ID from that user's Apps Script project settings (for `pipeline-decisions`: the Pipeline workbook → **Extensions → Apps Script → Project Settings → Script ID**):

```sh
cp -n .clasp.example.json .clasp.json
grep scriptId .clasp.json
clasp status
```

`cp -n` never overwrites an existing `.clasp.json`, which is the only local record of the Script ID. Expected result: `grep` shows a Script ID, not `COPY_VERIFIED_SCRIPT_ID_FROM_PROJECT_SETTINGS`, and status lists the files that would upload: only `src/` modules, `.html` files and `appsscript.json`. Keep `"rootDir": "src"`.

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

### Deploy the web page after a change

`clasp push` updates the project's code, but the web app's `/exec` URL serves the deployed version. After pushing:

1. Prerequisites: the Decision Register has an **Options** tab (Decision ID, Code, Summary, Recommended, Key figures) and the Pipeline a **Steps** tab (Pipeline ID, Step, Task, Specialist, Status), header row only is enough. Without them the page falls back to the text in Master; with a tab but a missing column it stops with "Missing column … in the … tab".
2. From `google_appscript/pipeline-decisions`:

   ```sh
   npm test
   npm run clasp:push
   ```

3. In the Apps Script editor: **Deploy → Manage deployments**, select the existing web-app deployment, **Edit** (pencil), Version **New version**, **Deploy**. Keep the same deployment so `WEB_APP_URL` and the Extensions menu link stay valid; a *new* deployment gets a new URL.
4. Expected result: open the workspace from **Extensions → Horology — Pipeline decisions → Open Horology workspace**. A proposed decision with Options rows shows one card per row with the recommended one marked; an item with Steps rows shows **Planned steps**; a decided current decision on an Approved, Parked, Rejected, Rework or Completed item shows **Revise this decision**.
   Then check the loading behaviour:
   - The Decisions list appears with the page, with no separate "Loading decisions…" step.
   - Opening a decision or item shows "Loading …" briefly, and the address bar ends in `#decision/<ID>` or `#item/<ID>`; the browser's Back button returns to the list.
   - Searching the Pipeline for a word that appears only in an item's Next step finds it after a moment ("searching full text…").
   - An edit made directly in the sheet shows in the lists within a minute, or at once after **Refresh**.
   - Item 39's Next step shows each numbered step as one paragraph with its number (no "1." on a line of its own).
   - An item page has an **Agent and domain** section with five controls and **Save agent and domain**; Entity choices change with Domain. **Edit item** no longer has those fields.
   - The page has the dark top bar, IBM Plex Sans and the amber **Add item** button. Decisions shows the inbox beside the reading pane; Pipeline shows the five-column board, and a card opens the item. At phone width (or a narrow window) the inbox stacks above the decision and the board scrolls sideways.

   `appsscript.json` is unchanged by this release.
5. To roll back: **Manage deployments → Edit → Version**, choose the previous version, **Deploy**. Tabs and rows are additive, so the old code ignores them.

No data is deleted by this change. Revising a decision writes the Decision Register row (Status, Reason, Review source, and Decision or Rework instructions) and the item's Status, Stage, Agent status and Updated cells.

## Locations

The folder path browser and **Check Drive & update Locations** action are in the Horology web workspace’s **Folders** view. The web app may ask the owner to authorize read-only Drive access.

## ClickUp Sync

Standalone. In the project's **Project Settings → Script Properties**:

| Property | Value |
|---|---|
| `CLICKUP_TOKEN` | Your personal ClickUp API token (ClickUp settings → Apps). Type it here only. |
| `PIPELINE_SHEET_ID` | The user's Pipeline workbook ID, found between `/d/` and `/edit` in its URL |

Map an existing task by placing its full `https://app.clickup.com/t/...` URL in that Pipeline row's **ClickUp Pipeline URL** cell. AI can suggest a match, but confirm the task before saving its URL. Unlinked rows are ignored; this script does not create tasks. Several Pipeline items can share one task: each posts its own comment headed `Pipeline <ID> · <title>`, and the sync leaves a shared task's ClickUp status alone.

Then, in the editor:

1. `previewSync`: inspect the linked task IDs, proposed status changes and exact proposed comment in the Execution log. Writes nothing.
2. `applySync` once to align status. Each linked item with no `_ClickUp Sync` record yet gets one intro comment (Stage, Status and latest decision with a link); items already recorded are not re-introduced, and history is not reposted.
3. Make a small test change to a linked Pipeline row or its indexed documents, run `previewSync`, then `applySync`. Check that one comment appears and that repeating the run posts nothing. Completed posts a comment without changing the ClickUp status; close that task manually.
4. Run `installTriggers`. It keeps an existing hourly `applySync` trigger and adds the Pipeline onChange trigger (`syncOnPipelineChange`); neither is duplicated if it already exists. Approve the authorization prompt, which now includes the Pipeline workbook trigger. `installHourlyTrigger` and `installChangeTrigger` install one each; `removeChangeTrigger` removes only the onChange trigger; `stopSync` removes both.
5. Check both under **Triggers** (clock icon): `applySync` time-based hourly, and `syncOnPipelineChange` "From spreadsheet – On change".

To pause: `stopSync`, or `ENABLE_WRITES: false` in `src/Config.js` and push. With writes off, the onChange handler returns without syncing.

### Deploy the shared-task, intro and onChange version

Run from `google_appscript/clickup-sync` with `.clasp.json` pointing at the live project:

```bash
npm test
```

```bash
npx clasp status
```

```bash
npx clasp push
```

Then in the editor: `previewSync` and read the log. Items not yet in `_ClickUp Sync` (for example ones that shared a task and were blocked before) show an intro comment; shared tasks show no status change. If it looks right, run `applySync`, then `installTriggers`. To roll back, `stopSync`, check out the previous commit of `google_appscript/clickup-sync/src`, push and run `installHourlyTrigger`; `_ClickUp Sync` records written by the new version stay valid.

### Check which writes fire the onChange trigger

Expected: an edit you type in the Pipeline workbook fires it; writes through the Sheets API (agents, connectors) and from the web workspace's Apps Script may not. Confirm once after installing:

1. Type a change into a linked item's Stage cell. Within about a minute, **Executions** shows `syncOnPipelineChange` and, about 30 seconds later, ClickUp shows one comment for that item.
2. Change a linked item through an agent or the Sheets API, and separately through the Horology web workspace. Note whether **Executions** shows `syncOnPipelineChange` for each. Whatever doesn't fire is posted by the next hourly `applySync`.
3. Make several quick edits to one row. Expect several `syncOnPipelineChange` executions but one comment: earlier ones stop when a later change arrives.

The previous `LIST_<Domain>` Script Properties are ignored. They may be removed after the new version is verified.

## Troubleshooting

| Symptom | Check |
|---|---|
| Login expired or wrong account | `clasp login`, then `clasp show-authorized-user` |
| Script unavailable | The script ID, and the account's access to the project |
| "Request contains an invalid argument" on push or pull | `.clasp.json` still holds the template placeholder: `grep scriptId .clasp.json`, then put back the Script ID from Project Settings |
| Apps Script API disabled | Enable it in account settings and retry |
| Unexpected upload files | `.clasp.json` rootDir, `.claspignore`, `clasp status` |
| A menu is missing in the workbook | Reload the workbook; the menus are added when it opens |
| "Registers tab needs exactly one row matching…" | The Registers tab has one row named like the register, with a Google Sheets link |
| ClickUp item blocked "Task link conflicts with existing sync state" | Confirm the Pipeline URL, then reconcile the old task ID in `_ClickUp Sync` |
| ClickUp item blocked "Uncertain previous ClickUp write" | Inspect ClickUp for the comment before clearing the pending state; avoid duplicates |
| A ClickUp task's status doesn't follow Pipeline | More than one Pipeline item links that task; shared tasks only get comments |
| "Sync already running." in Executions | Another run held the lock; the change is posted by that run or the next hourly one |
| Remote edits differ | Compare as above before pushing |

Runtime errors are in each project's **Executions** view. `clasp run` needs extra API setup and isn't used here.
