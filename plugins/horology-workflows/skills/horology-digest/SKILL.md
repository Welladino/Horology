---
name: horology-digest
description: Daily report card for the founder as a Google Doc — Pipeline counts by status, what finished since the last digest with key findings and recommendations, what's waiting on the founder, and health and knowledge-graph checks. Use on a daily schedule or when asked for a digest or status report. Reports only; changes no work.
---

# Digest

## When to use

A scheduled daily run, or when the founder asks "what happened?", "give me the digest" or a status report. The digest reads and reports; it doesn't run, plan or decide anything.

## Required context and locations

- Read [domains, folders and templates](../horology-capture-triage/references/locations.md) before choosing a domain or entity, reading context or saving anything.
- Follow the [presentation rules](references/presentation.md) when creating or filling documents.
- Read [what to check](references/checks.md) for the data each section needs.
- Sources: [Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit) (Master), [Document Index](https://docs.google.com/spreadsheets/d/1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc/edit) and [Decision Register](https://docs.google.com/spreadsheets/d/1_megp_hD4gwRuF4wmk4g2vQGAWbLl4uNUpho-oLoygE/edit). Map columns by header name.
- Runs and item history come from the document-graph connector (`list_runs`, `get_item_history`); use the `horology-document-graph` skill for the graph checks. Say which checks were skipped when the connector isn't available.

## Workflow

1. Find the previous digest in the Document Index (Document Type report, title starting "Horology digest"). The period runs from its date to now; if there is none, use the last 24 hours.
2. Gather the data for each section in [what to check](references/checks.md).
3. For each item finished in the period, open its output documents and pull the key finding and the recommendation in a sentence or two each. Don't copy whole sections; the founder should be able to skip opening most reports.
4. Write the digest as a new Google Doc titled "Horology digest — YYYY-MM-DD", in the Agent output folder for digests in Locations, under the domain that holds the registers (the domain of the Pipeline's Sheet row). If there is none, use that domain's root folder and say in the digest that a digests folder should be added; this is the one exception to asking first, because digests run unattended. Use a digest template from the Templates tab if there is one.
5. The base content, in this order:
   - **Report card:** counts of Pipeline items by Status, by Agent status and by Agent type, and per domain; Ready and Plan counts stand out.
   - **Done since the last digest:** one row per finished item — item, specialists used, key finding, recommendation, link to the output, run status.
   - **Waiting on you:** items Awaiting decision (oldest first, with days waiting), proposed decisions, and Plan rows not yet planned.
   - **Health and graph checks:** only problems, each with what to do; a clean area gets one line.
6. Choose the presentation freely: tables, short prose, charts or diagrams, whatever makes the state quickest to grasp. Follow the presentation rules.
7. Charts and diagrams go in as images. A Google Doc can only take an image from a URL Google can fetch: insert one only where the platform can host the image privately for Google to read. Never make a file public to embed it. Otherwise put the chart on a Digest tab in the Pipeline workbook (native chart) and link to it from the Doc.
8. Register the Doc in the Document Index as Document Type report, Graph Inclusion FALSE, with the Domain of the folder it was saved in, so digests don't fill the knowledge graph with near-duplicates.

## Decision and permission boundaries

- Report only. Don't change Pipeline rows, claims, decisions or Graph Inclusion; recommend the action instead.
- Don't send email or messages unless the founder's request includes it; a scheduled send belongs to code (Apps Script or the GCP API), not this skill.
- Don't invent findings. If an output can't be opened, say so and link it.

## Output requirements

- One Google Doc per digest, linked in the reply, with the four base sections.
- A short reply: the link, the three numbers that matter most (Ready, awaiting decision, problems), and anything you couldn't check.

## Verification before finishing

- Re-read the Doc: every section present, tables readable, links working, no placeholder text.
- Check the report-card numbers against a second read of Pipeline Master.
- Confirm the Document Index row exists with Graph Inclusion FALSE.
