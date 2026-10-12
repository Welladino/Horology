# Horology plugin instructions and register prompts

## Source locations

- `personas/subscriptions/research.md`: Agent Register Master ID 1, Research prompt.
- `personas/subscriptions/technical-assessment.md`: Master ID 2, Technical Assessment prompt.
- `plugins/horology/`: Horology App-backed plugin manifests, preserved `.app.json` binding and the `horology-mcp-access` operating skill.

The two personas are subscription-agent prompts, not provisioned Hermes profiles. Their original Instructions / Prompt text is preserved under that heading. Keep the Research and Technical Assessment workflow skills installed separately; the gateway skill does not replace them.

## Register source pointers

Master `H1:H3` now uses header `Prompt source / link` and the two repository paths. GitHub links will be added later, after the files are published. Edit only those cells; preserve permanent agent IDs, schedules, platform/skill selection and formatting. Before replacing a pointer, verify the destination file exists and the exact prompt has been saved. The live register is [Welladino — Agent Register](https://docs.google.com/spreadsheets/d/1BBZNwuGodU6JlrCk-09L7aZ2BqOBED6Vir0vpDMiJoo/edit).

## Plugin maintenance

The existing private personal plugin is [Horology](https://chatgpt.com/plugins/plugin_asdk_app_6acc6833d128819185f9cf4241d60942), backend ID `plugin_asdk_app_6acc6833d128819185f9cf4241d60942`. This update is version 1.0.1, release `pluginrel_6accb189d62c819193ed45f45f6ab880`.

1. Read its latest source and current release through Plugin Creator before editing.
2. Edit the scoped skill under `plugins/horology/skills/`. Preserve App identity, `.app.json`, OAuth/MCP connection, presentation and default prompts.
3. Bump versions consistently in `plugin.json` and `.codex-plugin/plugin.json`.
4. Validate skill frontmatter and the portable manifest. Compare App/presentation/configuration with the previous release.
5. Zip the plugin folder under its manifest name, preserving hidden files, outside the source folder. Include only plugin package files, not the server credentials or repo.
6. Update the existing plugin with its observed release ID, then read back the changed files and confirm its identity and App binding are unchanged.
7. Check `gateway_status` for connectivity without invoking paid provider tools.

Existing tools remain supplied by the App connection. A saved skill release does not prove it has reloaded into an already open chat; verify discovery in a refreshed host before claiming the host used the new skill. No server redeployment or OAuth reconnect is required just to save these instructions.

## Read capability expansion (1.0.2)

Release pluginrel_6accc08041f0819195ce29023943ab84 updates the skill for fixed Alexandria reads and bounded Tavily extraction. The App binding is unchanged. Google, GitHub writes and DataForSEO remain deferred. Refresh host tool discovery/instructions if new tools are absent; reconnecting is not a quota reset.
