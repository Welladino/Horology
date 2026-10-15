# Planning Workspace

Working area for research and implementation notes on Horology itself, including Hermes and subscription-agent infrastructure. Business outputs remain outside this repo: Hermes uses the Neon document graph; subscription agents use Drive and Sheets.

## Structure

- `docs/planning/research/` - discovery briefs: open questions, options considered, recommendation
- `docs/planning/notes/` - implementation notes: decisions made, rationale, what changed and why
- `docs/planning/templates/` - reusable templates for the above
- `docs/architecture/` - standing, current-state design reference (updated in place, not dated), one subfolder per area
- `docs/archive/` - completed/superseded planning docs, moved here once done
- `docs/runbook/` - practical how-to operational docs (setup, day-to-day commands), organized by topic subfolder

## Recommended File Naming

- `YYYY-MM-DD_topic-slug_research.md`
- `YYYY-MM-DD_topic-slug_note.md`

## Workflow

1. Open question or decision to make → start a research brief from `templates/RESEARCH_BRIEF_TEMPLATE.md`.
2. Decision made / implementation done → capture it in `templates/IMPLEMENTATION_NOTE_TEMPLATE.md` under `notes/`.
3. If a later decision changes an earlier one, don't rewrite history — add a new note referencing the old one.
4. Add the note to the notes index.

## Notes Index

- `docs/planning/notes/index/HOROLOGY_NOTES_INDEX.md`

## Research Index

- `docs/planning/research/index/HOROLOGY_RESEARCH_INDEX.md`

## Archive Index

- `docs/archive/index/HOROLOGY_ARCHIVE_INDEX.md`
