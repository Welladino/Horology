# Plugins

- `horology-tools/`: the gateway skill (`horology-mcp-access`), and the OpenAI/Codex Horology App plugin.
- `horology-document-graph/`: the document-graph skill.
- `horology-workflows/`: supervisor, capture-and-triage, planner and digest skills (OpenAI/Codex identity `welladino-workflows`).

Each folder's `skills/` is the source for every platform. Claude takes each skill as a claude.ai upload, built with `scripts/ops/build_skill_zips.py`, not as a plugin: see [Claude skills and connectors](../docs/runbook/subscription-agents/claude_skills.md). The OpenAI/Codex manifests (`plugin.json`, `.codex-plugin/plugin.json`) package the same `skills/` for Codex.

Maintain each folder's skills, referenced assets and Codex manifests together. Installed copies and account releases are distributions, not source. Publishing is separate from repository edits.

- `horology-specialists/`: specialist skills the supervisor hands items to (research, technical assessment, security review, GTM, marketing strategy, content planning).

Apps Script code lives in `google_appscript/` (`pipeline-decisions/`, and the optional `clickup-sync/`). Agent instructions are the skills in these plugins; Hermes profiles will move to the same structure when Hermes is set up again.
