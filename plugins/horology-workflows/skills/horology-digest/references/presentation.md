# Presenting documents

Choose the structure that makes the content quickest to understand. Templates show patterns; a document doesn't need every pattern.

## Structure

- Prose for context, reasoning and contingencies, one main idea per paragraph.
- Bullets for parallel findings, dependencies, assumptions or open questions.
- Numbered lists for ordered steps or milestones, not arrow chains inside a sentence.
- Tables to compare options on the same criteria, or to track milestones when owner, timing and evidence need their own columns. Use a list for a simple sequence.
- Headings to separate sections, using real heading styles, not bold text.
- Keep metadata, evidence, recommendations and decisions apart. Don't invent owners, dates or commitments.

## Native formatting

- Use the document's own lists, headings and tables. Typed bullet characters, typed numbers, Markdown tables and raw Mermaid text don't count.
- Keep tables narrow, with a clear header row. Don't use a table for prose or a single fact.
- Use descriptive link text, and keep Workspace chips and useful links to locations.
- When filling a template, keep each field's role, adapt its example lists and columns to the question, and remove instructions and optional sections that don't apply.

## Visuals

Every Research, Direction, Plan and Technical Assessment document carries a visual by default:

| Document | Default visual |
| --- | --- |
| Research | Options or evidence chart, from real figures only |
| Direction | Audience or positioning diagram |
| Plan | Milestone timeline or process flow |
| Technical Assessment | Effort–uncertainty quadrant, plus a current-vs-proposed diagram |

- Skip a visual only by writing `No visual: <reason>` in the Visuals section, for example "No visual: no comparable figures exist yet". In a Technical Assessment the quadrant and current-vs-proposed subsections are its Visuals section; each needs its visual or its own line.
- Never draw a chart from qualitative claims or invented numbers. If the figures don't exist, draw a diagram instead or write the No visual line.
- Diagrams: write the editable source (Mermaid, Graphviz or similar), render it to PNG, insert the PNG and keep the source beside the document or link it. Keep the two in step when revising.
- Charts: render a PNG from the data and label it as a snapshot. Link the data (a Sheet or CSV beside the document) and say it needs refreshing to update.
- Every visual gets a caption, a sentence on what it shows and a link to its source. Charts also give the data source, units, period and assumptions. Add alt text (the image description).

### Inserting the image into a private Google Doc

Docs `insertInlineImage` fetches its URI anonymously, so a private Drive file link (`drive.google.com/uc?id=…` or a `/view` link) is refused as "not publicly accessible". Never make a file public to get round this. Use this route, which works through the Drive and Docs connectors:

1. Render a PNG (or JPEG or GIF; Docs doesn't take SVG). Keep it small: a few colours, about 1200 px wide.
2. Upload a carrier Google Doc with Drive `create_file`: content type `text/html`, body `<img alt="…" src="data:image/png;base64,…">`. Drive converts it and embeds the image.
3. Read the carrier with Docs `read_doc` and copy the image's `inlineObjects.*.imageProperties.contentUri`. It is short-lived, so use it straight away.
4. In the target document, call `insertInlineImage` with that `contentUri` at the Visuals section, then set its size and description. The target keeps its own copy of the image.
5. Trash the carrier Doc. Keep the PNG and its source in the document's folder as the editable source.

An image under about 1.5 KB can go straight into `insertInlineImage` as a `data:image/png;base64,…` URI, because Docs caps the URI at 2 KB; real charts are larger, so use the carrier route. If neither works on your platform, upload the PNG beside the document, link it from the Visuals section with its caption, and say in your report that the image is linked, not embedded.

## Check before handing off

- Steps and milestones are numbered lists or tables; dependencies, options and parallel findings are in lists or comparisons.
- The Visuals section has its default visual embedded (or linked, as reported) with a caption and source link, or a `No visual: <reason>` line.
- Headings and table headers explain the structure without extra sections.
- Read back the headings, lists, tables and links. Look for empty list items, leftover placeholders and lost content.
- When layout matters, look at a rendered preview. If you can't, say so: the document's structure alone doesn't prove how it looks.
- If the platform can't produce the native structure, say so and use a format the founder agrees to. Never deliver imitation formatting silently.
