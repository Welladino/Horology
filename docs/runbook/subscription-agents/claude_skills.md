# Claude skills and connectors

Claude gets Horology from your claude.ai account: two custom connectors for the MCP servers, and one uploaded skill per skill folder. They load in cloud sessions (whatever repository they clone, or none), claude.ai chat, Cowork, and Claude Code on this Mac. Plugins don't load in cloud sessions, so Claude doesn't use the folders in `plugins/` as plugins; they're the skill source, and the OpenAI/Codex packaging. Why: the [note](../../planning/notes/2026-10-17_claude-skills-and-connectors-on-claude-ai_note.md).

## Connectors

claude.ai → Settings → Connectors → **Add custom connector**, once per server:

| Server | URL |
| --- | --- |
| Gateway | `https://mcp-gateway-366292507424.us-central1.run.app/mcp` |
| Document graph | `https://document-graph-366292507424.us-central1.run.app/mcp` |

Sign in with Google when asked, as someone on the Audience test-user list and in the [users tables](../mcp/access.md) with a grant for that server (and, for the document graph, a workspace). In a cloud session or routine, switch on the connectors it needs.

## Skills

Edit skills in their source folders, `plugins/*/skills/<name>/`. Then build the zips, all of them or only the ones changed:

```bash
python3 scripts/ops/claude/build_skill_zips.py
```

```bash
python3 scripts/ops/claude/build_skill_zips.py horology-supervisor horology-planner
```

Zips land in `plugins/dist/claude/` (git-ignored), one per skill. A skill that links to another skill's reference files gets its own copy of them, since claude.ai keeps each skill separate.

Upload each changed zip: Customize (desktop app sidebar) or claude.ai skills settings → **Skills** → upload. Uploading a skill with an existing name replaces it. Keep each skill switched on.

```bash
open plugins/dist/claude
```

There are 12 skills: supervisor, planner, digest and capture-triage (`horology-workflows`); research, technical assessment, security review, GTM, marketing strategy and content planner (`horology-specialists`); `horology-mcp-access` (`horology-tools`); and `horology-document-graph`.

## Check

In a new cloud session (or a new local Claude Code session, where they show as `anthropic-skills:horology-*`):

- The `horology-*` skills are listed.
- With both connectors on: `gateway_status` (14 names: 13 tools plus the `tavily_advanced_search` permission) and `list_documents`. Neither makes paid calls. The document graph lists 19 tools.

If a tool or skill appears twice, an old Horology plugin is still installed on your account: remove it under Customize → Plugins.
