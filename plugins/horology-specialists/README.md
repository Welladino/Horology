# Horology Specialists plugin

Specialist skills the supervisor (`horology-supervisor`, in `plugins/horology-workflows/`) hands Pipeline items to. Each specialist is one skill under `skills/`, named in the Agent Register's Skills column so the supervisor can find it.

| Skill | Does |
| --- | --- |
| `horology-research` | Evidence, options and a recommendation for a business or technical question |
| `horology-technical-assessment` | Feasibility, options, effort, cost and uncertainty of a software change |
| `horology-security-review` | Read-only security review with prioritised findings |
| `horology-gtm` | Target customers, positioning, first channels and order |
| `horology-marketing-strategy` | A marketing plan from an agreed GTM direction |
| `horology-content-planner` | Content plans, briefs and draft copy |

To add a specialist: add `skills/<name>/SKILL.md` (and `agents/openai.yaml` for ChatGPT/Codex display), bump the versions in all three manifests, and add a row to the Agent Register.

Keep the Claude manifest (`.claude-plugin/plugin.json`) and the OpenAI/Codex manifests (`plugin.json`, `.codex-plugin/plugin.json`) in step when releasing. Install: [Claude plugins](../../docs/runbook/subscription-agents/claude_plugins.md).
