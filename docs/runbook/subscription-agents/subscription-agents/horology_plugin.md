# Horology plugin maintenance

The platform-independent skill source is `plugins/horology-*/skills/`. Each account plugin must contain exactly the skills under its corresponding source folder. Never add installed legacy skills to a new release merely because they were in an earlier account release.

All Codex configuration source belongs under `plugins/<folder>/.codex-plugin/`. Edit `plugin.json` there. Verified registered App mappings belong in `apps.json`. Shared skills, references and shared assets remain in their existing folders.

Run `python3 scripts/ops/codex/build_codex_plugins.py` from the repository root. It creates portable upload archives under ignored `plugins/dist/codex/`, generating any required root `plugin.json` and `.app.json` inside the archive. The MCP plugins use registered App connections; no separate source `mcp.json` is maintained. Do not copy generated manifests back to source.

Before publishing, read the account plugin's current inventory and release ID. Preserve its backend identity, App binding, authentication, presentation and audience. For App-backed plugins, update skills and version without changing the registered connection. Bump the source version and update using the observed release ID. Explicitly delete retired skill paths when the source no longer contains them; omission alone preserves them. Re-read the saved inventory and compare its skill names to the source.

The visible name must match the source folder. Platform-generated internal names such as `dev-*` or the existing immutable `welladino-workflows` identify installed account packages; do not recreate or rename them to make the source folder name match.

A bundled remote URL is not proof of cloud availability. Register hosted MCP servers through ChatGPT's Add custom MCP server flow with OAuth DCR and verify the connected state. Local `codex mcp login` is separate. Use `gateway_status` and a bounded document listing for smoke tests; do not spend paid search, scraping or embedding credits.

See [Codex setup](codex_setup.md) for current release identities and connection verification, and [Claude skills and connectors](claude_skills.md) for the independent Claude setup.
