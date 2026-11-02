# Drive-first agent documents and optional repo docs

## Context

The Stage 3 rule treated a planning note in Git as the deliverable, with a Google Doc copy in the Plans folder and a GitHub link on `main`. The plan for item 45 (HOR-8 D) was indexed by its GitHub link as Document 32, so the ClickUp sync had to accept GitHub links. That model does not fit Horology's use across repositories: a target repository may have no docs folder, and work may be on a branch other than `main`. The founder cleaned up item 45 by hand (the plan is now Document 34 in Drive and Document 32's row is gone) and set the rule on 02/11/2026 as a direct change, without an investigation.

## Decision

- **Every deliverable lives in Drive.** Drive URL is always a Drive link. Agents keep choosing the template and folder under the existing Locations and Templates rules; no template is mandatory.
- **A repo doc is optional and follows the repository.** It is added only when the target repository already keeps its own docs, in that repository's structure, naming and templates. Otherwise nothing is added and no folder is created.
- **The branch comes from the item.** The doc goes on the item's GitHub branch, or the run's working branch when that field is blank, never `main` by assumption. Related Repo Document links to the doc on that branch.
- **Drive wins.** The repo doc names the Drive document by Document ID, and the Drive document wins on conflict.
- **Nothing is asked of the target repository.** Its `CLAUDE.md`, `AGENTS.md` and similar files are not changed to record Horology workflow. The rule lives in the skills, which travel with the agent.
- **Implementation route unchanged.** Steps rows remain the plan on that route. The Drive rule applies when a run writes a plan document.

## What changed

- `horology-research/references/linking.md`: the Document Index rule and a new repo doc paragraph.
- `horology-technical-assessment/SKILL.md` and `horology-supervisor/SKILL.md`: Drive first, repo doc only where the linking rules allow one.
- `google_appscript/clickup-sync`: `REPO_URL` removed from `Documents.js`, so a GitHub link in Drive URL is skipped with a log line.
- `docs/architecture/subscription-agents/workspace-records.md`: the same rule; the Document 32 exception removed.
- The HOR-8 D note's header names Document 34 as the canonical plan.

## Verification

- `.venv/bin/python -m pytest tests/unit -q` and `npm test` in `google_appscript/clickup-sync`.
- Not verified live: no `clasp push` or skill upload was made.

## Founder steps

1. In `google_appscript/clickup-sync`, run `npx clasp push`.
2. Rebuild and upload the changed skills on claude.ai ([runbook](../../runbook/subscription-agents/claude_skills.md)), and rebuild the Codex plugins as usual: `python3 scripts/ops/claude/build_skill_zips.py horology-research horology-content-planner horology-marketing-strategy horology-security-review horology-synthesis-artifacts horology-gtm horology-technical-assessment horology-supervisor`. The first six and the assessment bundle `linking.md`.
