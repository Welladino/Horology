# clasp: Apps Script source management

Use clasp to maintain the existing Welladino — ClickUp Sync project from Git. Commands below match the locally verified clasp 3.1.0 CLI. Run component commands from `google_appscript/clickup-sync/` unless stated otherwise.

## Set up the local CLI

From the Horology root:

```sh
cd google_appscript/clickup-sync
npm install
npx clasp --version
```

The package pins clasp 3.1.0. `npx clasp` uses the installed project dependency; the npm scripts use it too. Installing dependencies does not publish or execute Apps Script.

Enable the Apps Script API for your Google account at [Apps Script settings](https://script.google.com/home/usersettings) if required, then authenticate:

```sh
npx clasp login
npx clasp show-authorized-user
```

Choose the account with access to the intended project. For a session without a local browser callback, use `npx clasp login --no-localhost`. Login credentials belong in clasp's user store, outside this repo; do not paste them into source or commit them.

## Connect the existing project

The existing [Welladino — ClickUp Sync project](https://script.google.com/home/projects/1P-mmyz1d65liEF77KaeKabtV855aAlj6Oyk9WKkhfDlT4Eoe3wSFDfGU/edit) has script ID:

```text
1P-mmyz1d65liEF77KaeKabtV855aAlj6Oyk9WKkhfDlT4Eoe3wSFDfGU
```

Verify it in the editor's Project Settings. This is a script ID, not a deployment ID, spreadsheet ID or ClickUp list ID.

If `.clasp.json` is absent, copy the template:

```sh
cp .clasp.example.json .clasp.json
```

Replace its placeholder with the verified script ID and retain `"rootDir": "src"`. If the file already exists, inspect it rather than overwriting it. `.clasp.json` is ignored by Git.

```sh
npm run clasp:status
npx clasp open-script
```

Status lists local files selected for upload; it does not compare them with remote contents or execute functions. Only source modules and `appsscript.json` under `src` belong in the upload. Keep the exported `.js` filenames; do not add duplicate `.gs` modules.

## Compare browser edits safely

Do not pull directly into a working checkout with changes to preserve. Download into a separate temporary directory. From the component directory:

```sh
sync_component_dir="$PWD"
clasp_compare_dir="$(mktemp -d /tmp/welladino-clasp-compare.XXXXXX)"
cd "$clasp_compare_dir"
"$sync_component_dir/node_modules/.bin/clasp" clone 1P-mmyz1d65liEF77KaeKabtV855aAlj6Oyk9WKkhfDlT4Eoe3wSFDfGU --rootDir src
diff -ru "$sync_component_dir/src" "$clasp_compare_dir/src"
cd "$sync_component_dir"
```

`diff` exits with status 1 when files differ; that is expected. Review differences, merge selected changes into tracked source and rerun offline tests. Keep the temporary copy until reconciliation is complete. `clasp pull` fetches into the connected local project and can replace local files; use it only when that replacement is intentional.

## Verify and publish source

1. Confirm the project ID, pilot IDs and domain/list mapping. Keep `CLICKUP_TOKEN` only in Apps Script Script Properties. Sheet and list IDs remain in the non-secret configuration modules.
2. Inspect existing Apps Script triggers and pause sync writes during rollout where needed. Uploaded code can be used by existing triggers.
3. Run local checks:

```sh
npm test
npm run clasp:status
git diff --check
git diff -- src
```

4. Review and authorise the intended upload, then run:

```sh
npm run clasp:push
```

Push updates the connected project's source. Avoid `--force` and `--watch` for routine updates. Source push is separate from creating a deployment, running a function or installing a trigger. This sync does not require a new web-app deployment merely to update source.

5. In the Apps Script editor, run `previewSync`. Check the proposed task, status and comment changes against the selected pilot rows. Preview does not write to ClickUp. Follow the [sync workflow](../../../google_appscript/clickup-sync/WORKFLOW.md) before enabling writes and running `applySync` or installing a trigger. Restore intended write/trigger settings only after verifying the result.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Login expired or wrong account | Run `npx clasp login`, then `npx clasp show-authorized-user`. |
| Script unavailable | Confirm script ID and account permissions in the editor. |
| Apps Script API disabled | Enable it in account settings; retry the intended operation. |
| Unexpected upload files | Check `.clasp.json` rootDir, `.claspignore` and `npm run clasp:status`. |
| Connection test works but sync fails | Check Pilot IDs, live sheet headers, domain/list mapping and token access. |
| Remote edits differ | Clone into a temporary directory and reconcile before pushing. |

Use the Apps Script editor's Executions view for runtime errors. `clasp run` requires separate API-execution setup; it is not necessary for the editor-based preview/apply workflow. Never log authentication files, Script Properties values or request authorization headers.
