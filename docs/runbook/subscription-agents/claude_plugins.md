# Claude plugins

The repository root is a Claude plugin marketplace (`.claude-plugin/marketplace.json`, name `horology`) listing three plugins:

| Install id | Folder | Brings |
| --- | --- | --- |
| `horology-tools@horology` | `plugins/horology/` | `horology-mcp-access` skill + gateway connector (`.mcp.json`) |
| `horology-document-graph@horology` | `plugins/horology-document-graph/` | `horology-document-graph` skill + document-graph connector (`.mcp.json`) |
| `welladino-workflows@horology` | `plugins/welladino-workflows/` | capture, research and technical-assessment skills (Google Drive/Sheets come from your own connectors) |

Each plugin folder keeps one `skills/` directory shared by its Claude manifest (`.claude-plugin/plugin.json`) and its OpenAI/Codex manifests (`plugin.json`, `.codex-plugin/plugin.json`). The gateway plugin's Claude name is `horology-tools`; its ChatGPT App identity (`.app.json`) is unchanged.

## Validate after editing

```bash
command claude plugin validate .
```

```bash
for p in plugins/horology plugins/horology-document-graph plugins/welladino-workflows; do command claude plugin validate "$p"; done
```

## Install in Claude Code (this Mac)

From the repository root. A local marketplace loads plugin files in place, so later edits apply at the next session or after `/reload-plugins`.

```bash
command claude plugin marketplace add ./
```

```bash
command claude plugin install horology-document-graph@horology
```

Install the others the same way (`horology-tools@horology`, `welladino-workflows@horology`). The first tool call opens a browser for Google sign-in; use an Audience test user mapped to a workspace.

If the same server is already added as a claude.ai connector (for example "Horology document graph"), Claude Code shows both; remove one to avoid duplicate tools.

## Install in Claude (Cowork / claude.ai)

Plugins are uploaded as files: zip one plugin folder (not the repository), then Customize → Plugins → upload. Leave out `.DS_Store`; the OpenAI and Codex manifest files can stay in, as Claude ignores them.

```bash
cd plugins && zip -r ../horology-document-graph.zip horology-document-graph -x '*.DS_Store' && cd ..
```

The zip is a build artifact; don't commit it. Sign in to the bundled connector when Claude first asks.

## Status (2026-10-13)

- **Claude Code:** all three plugins are installed from this marketplace (user scope), and both connectors are signed in. Verified calls:
  - document graph: `list_documents`;
  - gateway: `gateway_status` and `supabase_list_schema`.
- **Cowork:** the three plugin zips were built and uploaded by the operator, and the document-graph plugin appears there. The workflow skills read the Workflow Guide and Agent Location Directory through the Google Drive connector.
