# Implementation Note

## Topic
- skill-scoping-per-profile

## Context

Noticed that new profiles (`gtm-manager`, `marketing-executive`) inherited Hermes's full set of 71 bundled skills by default — including `python-debugpy`, `github-pr-workflow`, `computer-use`, `comfyui`, `llama-cpp`, and dozens of others with no relevance to their actual roles (GTM strategy, marketing content). This is the same category of concern as the earlier code-execution-vs-MCP decision: an autonomous subagent shouldn't hold broad, unused capability just because it happened to ship with the platform's default profile template.

Unlike `delegate_task` (which cannot restrict tools per subagent — a known, accepted limitation noted in the migration-to-kanban-profiles note), profiles genuinely can be scoped, since skills are configured per-profile, not globally.

## Decision

Trimmed both profiles to the minimum justified skill set:

- **`gtm-manager`**: opted out of bundled skills (`hermes -p gtm-manager skills opt-out --remove --yes`, which also deleted the 71 unmodified bundled skills from that profile), then manually copied back only `arxiv`, `grounded-citations`, and `blogwatcher` (research-category skills relevant to market/GTM research) from the default profile's `skills/research/` folder — `hermes skills repair-official` didn't recognize these as restorable "official optional" skills, so a direct file copy was used instead. Verified via `hermes -p gtm-manager skills list` (3 enabled, correct set) and a live chat query confirming the profile still has full access to the document-graph MCP tools (unaffected — skills and MCP connections are separate systems).
- **`marketing-executive`**: opted out with the same `--remove` flag, left at zero bundled skills — copy/content work didn't have an obvious justified skill from the bundle. Can add specific ones later if a real need appears (e.g. a design/creative skill if visual content becomes part of the role).

## Rationale

This is the first point in the project where subagent scoping can actually be enforced at the platform level rather than only as a soft persona instruction (unlike `delegate_task`, whose lack of per-subagent tool restriction was an accepted limitation, not a choice). Given the principle already applied to the document-graph MCP server (narrowest useful capability, not broad access "just in case") and the earlier rejection of giving agents unscoped code execution, leaving 71 unrelated skills enabled on a strategy-only subagent was an inconsistency worth fixing once the tooling made it possible.

## Impact

- Any future subagent profile should default to `--no-skills` at creation (or an immediate opt-out) rather than starting from the full bundled set, then have skills added deliberately and individually.
- `hermes skills repair-official` is not the right tool for restoring specific bundled (as opposed to "official optional") skills — direct copy from `hermes-data/skills/<category>/<skill>/` into the target profile's `profiles/<name>/skills/<category>/` is the working method found here.

## Follow-Ups

- If Marketing Executive later needs a specific skill (e.g. for visual/design content), add it the same way — copy the specific skill folder, don't opt back into the full bundle.
- Consider whether this same trimming should be applied to Second-Soul's own (default) profile, which currently still has the full bundled set — not addressed in this pass, since Second-Soul's broader coordinating role makes its actual skill needs less obviously narrow than a single-domain subagent's.
