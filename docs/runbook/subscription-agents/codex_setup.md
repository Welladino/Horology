# Horology Codex setup

Horology has four plugins, matching the source folders under `plugins/`. Skills are maintained only in those folders; account releases are distributions.

| Source folder | Skills | Account plugin |
| --- | ---: | --- |
| `horology-tools` | 1 | [horology-tools](https://chatgpt.com/plugins/plugin_asdk_app_6ad311aa3a5881919a224275ae1b87b3) |
| `horology-document-graph` | 1 | [horology-document-graph](https://chatgpt.com/plugins/plugin_asdk_app_6ad31252859c8191b5e7fb52b2dd57ab) |
| `horology-workflows` | 7 | [horology-workflows](https://chatgpt.com/plugins/plugins_6ac8febac3148191a4f7292de35012fe) |
| `horology-specialists` | 7 | [horology-specialists](https://chatgpt.com/plugins/plugins_6ad30da5a8c88191a5e5972ba7ae6a66) |

The workflow plugin contains capture-triage, digest, planner, supervisor, template, watcher-setup and workspace-setup. The specialist plugin includes Stage 4 synthesis alongside research, technical, security, GTM, marketing and content skills. The obsolete `welladino-*` skill copies were removed from the workflow release. Platform-generated internal package names may differ from visible names; preserve backend identities on updates.

## Connections and verification

Install the account plugins and complete Google sign-in for the two MCP connections. Google Drive/Docs/Sheets and optional ClickUp remain separate workflow dependencies. Native ChatGPT MCP registration is required for the hosted connections: a bundled HTTPS MCP declaration alone can produce a desktop-only plugin.

For a smoke test in fresh local and cloud chats, check the 16 expected skills, then call `gateway_status` and a bounded `list_documents`. The current gateway status contains 14 callable tools plus the `tavily_advanced_search` permission; the document graph contains 19 tools. Avoid paid searches, scraping, embeddings, graph writes, syncs and run claims for connectivity checks.

## Existing local CLI connections

Local Codex also has direct MCP entries named `horology` and `horology-document-graph`. Their OAuth login can be renewed with:

```sh
codex mcp login horology --oauth-client-registration dcr
codex mcp login horology-document-graph --oauth-client-registration dcr
```

These local entries do not configure cloud connections. Avoid enabling duplicate tool sources in the same session. See [Codex plugin maintenance](codex_plugin_maintenance.md) for guarded account updates; building an archive does not publish it.

## For maintainers

Building, versioning and updating the existing account releases are intentionally kept in [Codex plugin maintenance](codex_plugin_maintenance.md). Claude has a separate distribution process in [Claude skills and connectors](claude_skills.md).
