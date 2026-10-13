# Plugins

- `horology/`: Horology MCP gateway plugin and operating instructions (Claude name `horology-tools`).
- `horology-document-graph/`: document-graph connector and skill (Claude only so far).
- `welladino-workflows/`: capture, research and technical-assessment workflow plugin.

Each folder can hold a Claude manifest (`.claude-plugin/plugin.json`) next to the OpenAI/Codex manifests; they share `skills/`. The repository root `.claude-plugin/marketplace.json` lists them for Claude. See [Claude plugins](../docs/runbook/subscription-agents/claude_plugins.md).

Maintain each plugin's manifest, skills and referenced assets together. Installed copies and account releases are distributions, not source. Publishing is separate from repository edits.

ClickUp synchronization code lives in `google_appscript/clickup-sync/`; agent prompts live in `personas/subscriptions/`.
