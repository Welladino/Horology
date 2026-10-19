# Apps Script projects: setup and publishing

Three projects, each in its own folder under `google_appscript/`; what they do is in the [Apps Script architecture](https://github.com/Welladino/Horology/blob/main/docs/architecture/subscription-agents/apps-script.md). Run each project's commands from its folder.

| Project | Folder | Script ID | Attached to |
|---|---|---|---|
| [Horology — Pipeline decisions](https://script.google.com/d/16wWrpPS5GnmZck7ZSKXPV61by7_Vy8vXjAj-ddSAt5N7pDtMnxv5m5Iy/edit) | `pipeline-decisions/` | `16wWrpPS5GnmZck7ZSKXPV61by7_Vy8vXjAj-ddSAt5N7pDtMnxv5m5Iy` | Pipeline workbook |
| [Horology — Workbook](https://script.google.com/d/1kG83_A4JUJ00QryyZHEV4oxVJKr6_-bBIcbvCWJZ6hdxwLfL_A4yKpKj/edit) | `pipeline-locations/` | `1kG83_A4JUJ00QryyZHEV4oxVJKr6_-bBIcbvCWJZ6hdxwLfL_A4yKpKj` | Pipeline workbook |
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

Bound to the Pipeline workbook. Reload the workbook after a push, then use **Extensions → Horology — Pipeline decisions**:

1. **Preview decisions** and check the list (approve access the first time).
2. **Install triggers**: every 10 minutes, and after each Decision Register edit.

**Stop triggers** removes them. In a copied workbook, check its Registers tab links its own Decision Register, then run Install triggers.

## Locations

Bound to the Pipeline workbook. Reload the workbook after a push, then use **Extensions → Horology — Workbook → Show folder structure** or **Check folders against Drive** (approve access the first time).

## ClickUp Sync

Standalone. In the project's **Project Settings → Script Properties**:

| Property | Value |
|---|---|
| `CLICKUP_TOKEN` | Your personal ClickUp API token (ClickUp settings → Apps). Type it here only. |
| `PIPELINE_SHEET_ID` | The Pipeline workbook ID: `1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI` |
| `LIST_<Domain>` | One per mirrored domain, spelled as on the Domains tab, e.g. `LIST_Horology` = `901820246905`, `LIST_Article Aggregator` = `901816729049` |

To find list IDs, run `discoverClickUpLists`, or take the number after `/li/` in the list's URL.

Then, in the editor:

1. `initializeSheets`, once per workbook: adds any missing fields; no ClickUp access.
2. `previewSync`: check the Execution log lists the items, task changes and comments you expect. Writes nothing.
3. `applySync` once, and check the tasks and comments in ClickUp. Run it again to confirm nothing is duplicated.
4. `installHourlyTrigger` to run every hour. `stopSync` removes it.

To pause: `stopSync`, or `ENABLE_WRITES: false` in `src/Config.js` and push.

To add a domain: add its Root folder row in Locations, then its `LIST_<Domain>` property. To stop one: delete the property.

## Troubleshooting

| Symptom | Check |
|---|---|
| Login expired or wrong account | `clasp login`, then `clasp show-authorized-user` |
| Script unavailable | The script ID, and the account's access to the project |
| Apps Script API disabled | Enable it in account settings and retry |
| Unexpected upload files | `.clasp.json` rootDir, `.claspignore`, `clasp status` |
| A menu is missing in the workbook | Reload the workbook; the menus are added when it opens |
| "Registers tab needs exactly one row matching…" | The Registers tab has one row named like the register, with a Google Sheets link |
| ClickUp item blocked "Missing or duplicate domain mapping" | A `LIST_<Domain>` property spelled as on the Domains tab |
| ClickUp item blocked "Domain/list changed" | Move the task in ClickUp, then fix its entry in the `_ClickUp Sync` tab |
| Remote edits differ | Compare as above before pushing |

Runtime errors are in each project's **Executions** view. `clasp run` needs extra API setup and isn't used here.
