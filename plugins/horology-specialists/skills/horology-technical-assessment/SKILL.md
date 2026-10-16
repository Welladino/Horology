---
name: horology-technical-assessment
description: Investigate a selected software change before committing to implementation. Inspect the target repo, derive and answer investigation questions, compare technical options and costs, and save a Stage 1 assessment for a founder decision.
---

# Technical assessment

## When to use

Use for Stage 1 evaluation of a code-related Pipeline item, including Feature, Enhancement, Refactor, or a known issue needing scope/feasibility assessment. A known symptom can shorten the investigation; it does not prove the diagnosis. This skill produces an assessment, not implementation or a Stage 3 repo planning note.

## Required context and locations

- Read the current [Workflow Guide](https://docs.google.com/document/d/1CdytxCa2c-M7KroQ05JO52_mVhogQ5J_acBhRDRsF5I/edit), [Location Directory](https://docs.google.com/document/d/1LZjDIqlRGYZjw_f1XgfEWzLqKOMjNWBS4Fz9afw18Ao/edit), and [Presentation Guide](https://docs.google.com/document/d/1D2N9VJRCmBFJ4T9cUGH47zQUVqk99sjavpbbwYIYY8I/edit).
- Read [output and linking rules](references/output.md) when saving the assessment or generating the quadrant.
- Resolve the permanent numeric Pipeline ID and bounded question from the request. Map live Master headers by name; columns may move. External ID is optional. Entity is blank for Article Aggregator, Welladino and Horology.
- Read Link type, URL, and GitHub branch. Verify the repository remote, target branch, and inspected commit before making code claims. Do not assume the current checkout is the requested branch or switch a dirty checkout to inspect it. Use read-only Git revision reads or an available matching checkout when appropriate. Report inaccessible branch/source evidence and clarify an ambiguous target.
- Agent type Manual means founder-led exploration, skipped by scheduled agents even if Ready. Ready is a selection signal, not an automatic launch. Explicit user assignments can select work directly.

## Workflow

1. Read repo instructions. For Article Aggregator, inspect graphify-out/GRAPH_REPORT.md or graph.json and relevant architecture maps before broad searches; then inspect scoped source, callers, state, dependencies, and tests at the verified revision.
2. Derive investigation questions from the reported impact and the implementation. Refine them as evidence emerges. Investigate each material question; record its answer, evidence, and remaining gap. Separate reported symptoms, verified source behaviour, live observations, and assumptions. Do not present a fixed generic checklist as findings.
3. Establish the current baseline and the smallest useful change. Reason beyond today's design: consider simplification, removing the need, reusing an existing capability, open-source libraries, managed services, and alternative architectures when credible. Investigate material alternatives with primary documentation and current pricing when relevant. Do not force a paid service or a fixed number of options into every assessment.
4. Compare each credible option against what exists today: expected benefit, one-off implementation and migration effort, direct/provider costs, recurring usage, maintenance, integration, reversibility, reliability, access/security constraints, and vendor dependence where material. State workload assumptions, currency/units, evidence date, and unknowns. A library being free does not make integration free; Unknown is not zero.
5. Explain Low / Medium / High or Unknown effort and uncertainty ratings. Use bounded estimates only when evidence supports them; do not invent precise hours or prices. Uncertainty means unresolved facts affecting feasibility, behaviour, cost, or validation. Recommend proceed, further investigation, or park with reasons and a revisit trigger when useful.
6. Copy the native Technical Assessment template into the verified technical Research destination. Adapt depth to the change. Fill native tables, derive the top summary and quadrant from the same evidence, retain editable visual sources, and link supporting evidence. Save the document and register links according to output.md.
7. Set Pipeline Awaiting decision only when the selected assessment is ready for founder review. Leave material blockers visible. Draft a proposed decision only when the requested workflow includes one. Stop at assessment; an accepted decision can separately authorise Stage 3 creation of a repo planning note using that repo's existing template.

## Decision and permission boundaries

- Do not implement fixes, install project libraries, run deployments/migrations, provision paid services, or execute live/provider-cost tests merely to prepare the assessment.
- Use existing evidence and safe read-only inspection. Explain evidence gaps instead of claiming tests or live configuration were checked when they were not.
- The founder decides proceed, rework, park, or reject. Recommendations, quadrant position, Type, and Ready are not acceptance.
- Preserve document and decision history. Small corrections update a document; substantive rework retains the prior revision and links its replacement. Never claim proposed register columns or graph imports already exist.

## Output requirements

- A concise assessment with metadata, summary, verified problem/impact, investigation questions and answers, current implementation/dependencies, alternatives, cost/effort/uncertainty reasons, validation approach, and recommendation/open questions.
- Top summary: Effort, Direct cost, Ongoing cost, Uncertainty. Include reasons and Unknown where appropriate.
- An effort-versus-uncertainty quadrant image with labelled option markers when rated, a caption, explanation, and editable-source link. Costs stay in the summary/table. Unknowns remain unplotted and listed. The template's unrated image is not a completed assessment visual.
- Native headings/lists/tables and evidence links; saved Pipeline and Document Index backlinks, with limits stated plainly.

## Verification before finishing

- Recheck repo/branch/commit, question evidence, estimates, current pricing sources where used, and consistency between recommendation, summary, and visual.
- Read back the document and linked records; preserve unrelated values. Verify native table structure, links, inserted image, readable labels, and removal of instructional placeholders.
- Inspect a rendered document when image placement/page fit matters; disclose unavailable visual QA. If the platform cannot render/embed the quadrant, report the limitation and provide the source plus textual ratings rather than silently omitting it.
- After uncertain write failures, inspect before retrying to prevent duplicates. Distinguish saved changes from pending writes.
