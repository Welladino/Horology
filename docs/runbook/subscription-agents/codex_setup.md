# Horology Codex setup

Horology has four plugins, matching the source folders under `plugins/`. Skills are maintained only in those folders; account releases are distributions.

| Source folder | Skills | Account plugin |
| --- | ---: | --- |
| `horology-tools` | 1 | [horology-tools](https://chatgpt.com/plugins/plugin_asdk_app_6ad311aa3a5881919a224275ae1b87b3) |
| `horology-document-graph` | 1 | [horology-document-graph](https://chatgpt.com/plugins/plugin_asdk_app_6ad31252859c8191b5e7fb52b2dd57ab) |
| `horology-workflows` | 4 | [horology-workflows](https://chatgpt.com/plugins/plugins_6ac8febac3148191a4f7292de35012fe) |
| `horology-specialists` | 6 | [horology-specialists](https://chatgpt.com/plugins/plugins_6ad30da5a8c88191a5e5972ba7ae6a66) |

The workflow plugin contains capture-triage, digest, planner and supervisor. The obsolete `welladino-*` skill copies were removed from its account release. Platform-generated internal package names may differ from visible names; preserve backend identities on updates.

## Source and builds

Codex metadata lives in each `.codex-plugin/plugin.json`. The two MCP plugins also have `.codex-plugin/apps.json`, referencing their registered ChatGPT App connections. The server URL and OAuth settings are held by those connections; no separate source `mcp.json` is maintained. Browser edits do not automatically update repository files.

Build from the repository root:

```sh
python3 scripts/ops/codex/build_codex_plugins.py
```

You can pass folder names to build a subset. The four archives are written to ignored `plugins/dist/codex/`. The builder generates root `plugin.json` and, where needed, `.app.json` inside each archive; those generated files do not belong in the source folders. Skills and their supporting files are packaged from the corresponding folder only.

For Claude's independent exports, run `python3 scripts/ops/claude/build_skill_zips.py`; its individual skill archives go to `plugins/dist/claude/`. See [Claude skills and connectors](claude_skills.md).

## Connections and verification

Install the account plugins and complete Google sign-in for the two MCP connections. Google Drive/Docs/Sheets and optional ClickUp remain separate workflow dependencies. Native ChatGPT MCP registration is required for the hosted connections: a bundled HTTPS MCP declaration alone can produce a desktop-only plugin.

As of 17 October 2026, local OAuth succeeded for both servers and gateway `gateway_status` passed. Native gateway registration and browser connection succeeded. Document-graph registration was created, but its authorization and final skill upload were interrupted and must be checked before claiming completion. A fresh Codex cloud session has not yet been verified.

The earlier desktop-only packages are not the canonical plugins linked above. Their removal was requested but interrupted; do not assume they were deleted or reinstall them:

- Old gateway: `plugins_6ad30d83658c8191b07efcfe95635503`.
- Old document graph: `plugins_6ad30d9624cc819187ab3c6a2d1ef423`.

For a smoke test in fresh local and cloud chats, check the 12 expected skills, then call `gateway_status` and a bounded `list_documents`. Avoid paid searches, scraping, embeddings, graph writes, syncs and run claims for connectivity checks.

## Existing local CLI connections

Local Codex also has direct MCP entries named `horology` and `horology-document-graph`. Their OAuth login can be renewed with:

```sh
codex mcp login horology --oauth-client-registration dcr
codex mcp login horology-document-graph --oauth-client-registration dcr
```

These local entries do not configure cloud connections. Avoid enabling duplicate tool sources in the same session. See [plugin maintenance](horology_plugin.md) for guarded account updates; building an archive does not publish it.
