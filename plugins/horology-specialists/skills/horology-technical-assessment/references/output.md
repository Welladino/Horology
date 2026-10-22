# Assessment output and linking

Copy the Technical Assessment template from the Templates tab into the Agent output folder for technical research (see the domains, folders and templates rules linked from SKILL.md). Never fill the template original during an assessment.

## Ratings and quadrant

Read scripts/render_quadrant.py when a renderer is needed. It requires Python and Pillow; use the platform's available plotting tools instead when needed, retaining editable source.

Supply JSON with title and options. Each option has name, effort, uncertainty, and optional recommended boolean. Ratings are Low, Medium, High, or Unknown (case-insensitive). Keep names short, use a few material options, and separate labels if points overlap. The ordinal coordinates do not represent measured numeric precision. Unknown effort or uncertainty is unplotted and listed below the chart.

Example invocation: python scripts/render_quadrant.py ratings.json quadrant.png.

Generate the top summary and JSON from the same evidence and written reasons. Direct and ongoing costs remain separate, with assumptions and units. Embed the image at readable document width, add a caption/explanation, upload ratings.json or another editable source beside the assessment, and link it. Verify the actual assessment visual; do not reuse the template's blank quadrant as the result.

## Shared records

Read live sheet metadata and headers before saving. Pipeline Master is the editable record. Resolve by permanent numeric ID, not row position or External ID. Agent type includes Manual; automated selection skips Manual. Link type/URL/GitHub branch identify the work target, while Document Index associates documents with Pipeline ID.

When writing Pipeline Summary / Why, Next step / Research question or Revisit trigger, or Decision Register Question, Decision, Reason or Rework instructions, use actual cell line breaks between distinct points. Put numbered steps on separate lines rather than in a run-on paragraph or literal `\n` text. Keep a short single thought on one line, preserve founder-written formatting, and read back multiline cells to verify the breaks.

Upsert [Document Index](https://docs.google.com/spreadsheets/d/1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc/edit) by Drive file ID/URL, preserving its document ID. Allocate permanent numeric Document IDs from live records and match dropdowns. Record the assessment as research, Draft, with Related Pipeline URL. Domain and Entity come from the Domains tab; set Entity only when the domain lists entities. Graph Inclusion is the founder's choice; rows set TRUE are copied into the document graph by the sync job.

In [Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit), update the specific next decision/question; record document links in Document Index. Set Awaiting decision when ready for founder review, not when evidence still blocks the assessment.

If included in the requested workflow, draft a proposed record in [Decision Register](https://docs.google.com/spreadsheets/d/1_megp_hD4gwRuF4wmk4g2vQGAWbLl4uNUpho-oLoygE/edit) Master, linking evidence and the Pipeline item. Do not accept a recommendation on the founder's behalf.

For substantive rework retain the prior document, link the new version and superseded document in metadata, and associate the latest revision with the same Pipeline ID in Document Index. Use the live revision/sequence and Supersedes document ID fields in Document Index, and Rework instructions in Decision Register. An assessment of an existing plan shares its Pipeline association without automatically superseding that plan. Verify exact headers and preserve document history.
