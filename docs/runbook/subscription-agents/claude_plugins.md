# Claude plugins

Four plugins, each a folder under `plugins/`:

| Plugin (Claude name) | Folder | Brings |
| --- | --- | --- |
| `horology-tools` | `plugins/horology-tools/` | `horology-mcp-access` skill + gateway connector (`.mcp.json`) |
| `horology-document-graph` | `plugins/horology-document-graph/` | `horology-document-graph` skill + document-graph connector (`.mcp.json`) |
| `horology-workflows` | `plugins/horology-workflows/` Supervisor, capture-and-triage, planner and digest skills; Drive, Sheets and ClickUp come from your own connectors |
| `horology-specialists` | `plugins/horology-specialists/` | Specialist skills: research, technical assessment, security review, GTM, marketing strategy, content planning |

Each folder keeps one `skills/` directory shared by its Claude manifest (`.claude-plugin/plugin.json`) and its OpenAI/Codex manifests (`plugin.json`, `.codex-plugin/plugin.json`). The OpenAI/Codex identities (`dev-6acc…` App, `welladino-workflows`, `horology-specialists`) are separate from the Claude names.

## Validate after editing

Bump the version in `.claude-plugin/plugin.json` whenever a plugin changes, so an upload replaces the old one.

```bash
for p in plugins/horology-tools plugins/horology-document-graph plugins/horology-workflows plugins/horology-specialists; do command claude plugin validate "$p"; done
```

## Build the zips

One zip per plugin folder, not the repository. `plugins/dist/` is gitignored.

```bash
mkdir -p plugins/dist && cd plugins && for p in horology-tools horology-document-graph horology-workflows horology-specialists; do rm -f dist/$p.zip; zip -qr dist/$p.zip $p -x '*.DS_Store' '*__pycache__*'; done && cd ..
```

## Install

Upload each zip in Claude: Customize → Plugins → upload. Uploaded plugins are saved to your account and stay private unless shared. Sign in to each bundled connector when Claude first asks, with a Google Auth Platform Audience test user (for the document graph, one mapped to a workspace).

Where they work:

- **claude.ai chat and Cowork:** yes.
- **Claude Code on this Mac:** account plugins sync in as `<name>@synced` (Claude Code v2.1.273 or later); run `/reload-plugins` or start a new session.
- **Cloud sessions (claude.ai/code):** plugins don't load there. Cloud sessions use claude.ai connectors you enable on the session and skills enabled on claude.ai.

If the same server is also added as a claude.ai connector, the tools appear twice; switch one off in that session.

To test an edited plugin locally for one session, without uploading:

```bash
claude --plugin-dir plugins/horology-document-graph
```

## Check after installing

These make no paid calls: `gateway_status` (14 names: 13 tools plus the `tavily_advanced_search` permission) and `list_documents`. The document graph should list 19 tools.
