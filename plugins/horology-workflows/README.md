# Horology Workflows plugin

Source of truth for the supervisor, capture/triage, planner and digest skills. Specialist skills live in [`horology-specialists`](../horology-specialists/).
Edit the instructions under `skills/` and keep the Claude manifest (`.claude-plugin/plugin.json`, name `horology-workflows`) and the OpenAI/Codex manifests (`plugin.json`, `.codex-plugin/plugin.json`, identity `welladino-workflows`) in step when releasing.

Moving or editing source does not publish a release or update installed copies. Google Drive/Docs/Sheets and ClickUp connections are configured separately.

Maintenance: [subscription-agent operations](../../docs/runbook/subscription-agents/operations.md). Claude install: [Claude plugins](../../docs/runbook/subscription-agents/claude_plugins.md).
