# Horology plugin sources

Each `horology-*` folder owns exactly the skills in its `skills/` directory. Claude skill exports and Codex packages both use these same files. Installed releases are distributions, never an additional skill source.

| Folder | Skills |
|---|---:|
| horology-tools | 1 |
| horology-document-graph | 1 |
| horology-workflows | 4 |
| horology-specialists | 6 |

Codex-specific source configuration belongs inside each `.codex-plugin/` directory:

- `plugin.json`: canonical Codex metadata, version and interface.
- `apps.json`: verified registered App bindings, when available. Do not invent or reuse deleted App IDs.

Shared `skills/`, references and assets remain outside `.codex-plugin/`. The obsolete `horology-tools/.app.json` referred to a deleted App and was removed; a backup is outside the repository.

## Build

From the repository root:

```sh
python3 scripts/ops/codex/build_codex_plugins.py
python3 scripts/ops/claude/build_skill_zips.py
```

Claude archives go to ignored `plugins/dist/claude/`, one per skill. Codex archives go to ignored `plugins/dist/codex/`. The builder creates the root `plugin.json` and `.app.json` paths required by the portable upload format inside the archive only. Do not copy generated root or compatibility files back into source, and do not install the source directory directly as a marketplace package; use the built package.

The existing workflow account plugin retains the immutable package name `welladino-workflows`; its visible name is `horology-workflows`. Use its existing backend ID on updates. Its release must contain only the four `horology-*` skills under `horology-workflows/skills/`, with no legacy `welladino-*` copies.

## Cloud MCP connections

MCP servers bundled into uploaded plugin archives can be marked desktop-only even with remote HTTPS endpoints. Register each endpoint through ChatGPT Plugins → Add → Add custom MCP server using OAuth DCR, then package its skill against the verified registered App connection. A successful local `codex mcp login` does not establish cloud authorization.

- Gateway: `https://mcp-gateway-366292507424.us-central1.run.app/mcp`
- Document graph: `https://document-graph-366292507424.us-central1.run.app/mcp`

Verify the actual web connection and one harmless tool read before claiming cloud support. Keep Google Drive/Docs/Sheets and any other workflow dependencies separately connected.
