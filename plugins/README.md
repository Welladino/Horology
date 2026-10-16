# Plugins

- `horology-tools/`: Horology MCP gateway plugin and operating instructions (Claude name `horology-tools`).
- `horology-document-graph/`: document-graph connector and skill (Claude only so far).
- `horology-workflows/`: supervisor, capture-and-triage, planner and digest workflow plugin (Claude name `horology-workflows`; its OpenAI/Codex manifests keep the `welladino-workflows` identity).

Each folder can hold a Claude manifest (`.claude-plugin/plugin.json`) next to the OpenAI/Codex manifests; they share `skills/`. See [Claude plugins](../docs/runbook/subscription-agents/claude_plugins.md).

Maintain each plugin's manifest, skills and referenced assets together. Installed copies and account releases are distributions, not source. Publishing is separate from repository edits.

- `horology-specialists/`: specialist skills the supervisor hands items to (research, technical assessment, security review, GTM, marketing strategy, content planning).

Apps Script code lives in `google_appscript/` (`pipeline-decisions/`, and the optional `clickup-sync/`). Agent instructions are the skills in these plugins; Hermes profiles will move to the same structure when Hermes is set up again.
