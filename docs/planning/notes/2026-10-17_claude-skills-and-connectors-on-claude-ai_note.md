# Implementation Note

## Topic
- claude-skills-and-connectors-on-claude-ai

## Context
- **Cloud sessions are where runs go.** The supervisor starts one session per Pipeline item, and Cloud runs use `claude --cloud`. Those sessions need the Horology skills and both MCP servers.
- **Plugins don't load there.** Claude Code's [cloud environment docs](https://code.claude.com/docs/en/cloud-environments#what-carries-over-from-your-setup) (checked 2026-10-17): neither plugins enabled in user settings nor ones a repository turns on in `.claude/settings.json` are installed in a cloud session. Our four Claude plugins, and the connectors bundled in their `.mcp.json`, never reached a cloud run.
- **What does load:** claude.ai connectors switched on for the session, skills enabled on the claude.ai account, and skills committed to the cloned repository's `.claude/skills/`.

## Decision
- **Connectors:** the gateway and the document graph are claude.ai custom connectors on the founder's account, added 2026-10-17. No server change: sign-in and the [users tables](../../runbook/mcp/access.md) already decide who gets in.
- **Skills:** each of the 12 skills is uploaded to claude.ai on its own, from a zip built by `scripts/ops/build_skill_zips.py`. Uploaded 2026-10-17; they appear in local Claude Code as `anthropic-skills:horology-*`.
- **Removed:** the Claude plugin manifests (`.claude-plugin/plugin.json`), both `.mcp.json` files, the `.claude/skills/` links and the Claude plugins runbook. Replaced by the [Claude skills and connectors](../../runbook/subscription-agents/claude_skills.md) runbook.
- **Kept:** the skill folders under `plugins/` as the one source, at the same paths (the document-graph image copies `horology-capture-triage/references/workflow.yaml`), and the OpenAI/Codex manifests, which Codex still uses.

## Rationale
- **claude.ai, not the repository.** `.claude/skills/` only helps sessions that clone Horology. Agents also work in other repositories, or none, and claude.ai skills load in all of them, as well as in chat and Cowork.
- **One zip per skill.** claude.ai takes one skill per upload, and no bulk upload was found. Merging skills into fewer uploads would blur the descriptions Claude chooses skills by.
- **Copied references.** claude.ai keeps each skill separate, so the seven skills that link to another skill's references (`linking.md`, `records.md`, `runs.md`, `workflow.yaml`) get their own copies in their zip. The source keeps one copy.
- **No duplicates.** Plugins or repo skills alongside the claude.ai ones would list each tool or skill twice.

## Impact
- **Releasing a skill change** is now: edit the source, rebuild that skill's zip, upload it. A change isn't live for Claude until it's uploaded.
- **Skill wording:** the supervisor, planner and routing reference name the specialist skills instead of "the Horology Specialists plugin", which is a Codex-only package now.

## Follow-Ups
- **Check a real cloud run** picks up the skills and connectors: a Ready item with Run location Cloud.
- **Codex** still installs the skills as plugins or local copies; unchanged here.
- **Agent Register** source pointers still name removed prompts ([horology plugin runbook](../../runbook/subscription-agents/horology_plugin.md)).
