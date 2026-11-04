# Pages tab for published pages

## Topic

- pages-tab

## Context

Stage 4 page addresses were stored nowhere the founder could see them. The Document Index has no URL field, and `horology-synthesis-artifacts` kept the alias in the HTML's metadata and said not to add a Sheet column for it, so the only way to find a page was to ask an agent or open Cloudflare. On 04/11/2026 the founder decided a new tab should list every past and new Cloudflare page with a description (Pipeline item 70, split from HOR-9).

## Decision

- **A Pages tab in the Document Index workbook**, one row per page address: Pipeline ID, Document ID, Title, Description, URL, Published (`DD/MM/YYYY`) and Run ID. Document ID is blank for a page with no Document Index row.
- **The publishing skill writes the row** after a verified publish, using the `url` the publish result returned rather than building `pipeline-<ID>.<project>.pages.dev` by hand (item 66 adds page-named branches). It finds an existing row by URL and updates it on a redeploy. Today `horology-synthesis-artifacts` is the only skill that publishes.
- **A test enforces it**: any skill whose files mention `publish_synthesis` must also mention the Pages tab (`tests/unit/workflow/test_skill_files.py`).

## Backfill

Cloudflare Access returns the same sign-in redirect for an address that was never deployed, so an unauthenticated request can't tell whether a page exists. Neither the Access sign-in nor the Cloudflare dashboard was signed in from the agent's browser, so the check used recorded publish results: the gateway returns a URL only after the deployment reaches `success`.

| Item | Result |
| --- | --- |
| 45 | Written. Run R-22's notes record the published URL (Document 33, 29/10/2026). |
| 39 | Written, though not on the original list. A 28/10/2026 session's publish result gives deployment `afa766b4`: a decision digest of items 39 to 42 published under item 39's address. It has no Document Index row. |
| 22 | Left out. No publish is recorded. Its synthesis (Document 24, 20/10/2026) is older than Pages publishing (22/10/2026). |
| 53 | Left out. Run R-33's notes say "Pages publish not attempted" for Document 40. |
| 38 | Left out. No publish to its address is recorded. |

## What changed

- Live: the Pages tab was added to the Document Index workbook with the two rows above. No existing tab or row was changed.
- `horology-synthesis-artifacts`: step 9 of `SKILL.md`, and a new "Pages tab" section in `references/visuals-and-pages.md` that replaces the "do not add a Sheet column" rule.
- `docs/architecture/subscription-agents/workspace-records.md`: the Pages tab and its row in the authority table.
- Codex plugin version: horology-specialists 0.2.10.

## Follow-ups

- The founder should open the two backfilled links while signed in to confirm they render. If another page was published from a session whose result wasn't kept, add its row by hand from the Cloudflare dashboard's deployment list.
- Item 66 makes `horology-mcp-access` a publisher too. Its "Record" step should add a Pages tab row; the new test fails at merge until it does.
- Rebuild and upload `horology-synthesis-artifacts` ([runbook](../../runbook/subscription-agents/claude_skills.md)) and the Codex specialists plugin.
