# Visual assets and private Pages publishing

## Make the visual earn its place

- Choose a comparison, timeline, process diagram, annotated screenshot, product image or chart only when it helps the founder understand a decision faster. Prefer one strong visual to several decorative ones.
- Python may be used to prepare and render charts. Derive plotted values from cited source data, keep the small data table or calculation beside the asset when useful, and check that labels and totals match the source. Use a restrained palette, direct labels, readable type, descriptive title, units, dates and a note for estimates or missing data. Avoid 3D, unexplained axes and crowded legends. Render SVG for sharp HTML/print output or a sufficiently large PNG when SVG is unsuitable. Check the rendered result at desktop, mobile and print sizes.
- For product or other source images, confirm that reuse is permitted, attribute the source and date, and keep the image with the artifact. Do not hotlink a private Drive file or an unstable third-party image. Do not make a private source public to obtain an image URL. If there is no suitable image or quantitative evidence, use a CSS or inline-SVG process/comparison graphic instead of a fabricated photo or chart.
- A Pages upload directory must contain `index.html` and every local image, font and chart it references, using relative paths such as `assets/chart.svg`. Keep external scripts and trackers out of a private briefing. Provide meaningful alt text and a text summary for each chart. Save the principal HTML in the verified Synthesis folder and supporting files in its Assets folder.

## Publish only to a verified private project

The Drive HTML and its Document Index entry are canonical. Cloudflare Pages is an optional viewing copy, not a new Pipeline stage or a replacement for Drive. The MCP gateway selects the registered Pages project from the signed-in email's sole workspace; the agent never supplies a project name. If publishing is unavailable, return the Drive artifact and report that it was skipped.

1. The gateway checks the live Pages project and both Access applications before uploading, including exact-email policies for the main `<project>.pages.dev` hostname and previews `*.<project>.pages.dev`. If it returns `needs_admin_setup`, tell the user to contact the Cloudflare administrator; keep the Drive synthesis and do not try another upload path.
2. Stage only this Pipeline item's `index.html` and assets. Call `publish_synthesis` with the Pipeline ID, full HTML, and any local images or CSS as `{path, base64}` assets. It publishes to the fixed `pipeline-<Pipeline ID>` branch under the workspace project. A later deployment for the same item updates that alias without replacing other items' branches. Do not upload source documents, credentials, raw research or unrelated files.
3. Read the deployment result and test the exact alias and at least one asset. Without an Access session, they must require authentication or deny access, never return the private HTML or image. Check the signed-in rendering if the run has an authorised session; otherwise give the founder the link and mark that visual check as pending. Record the page on the Document Index workbook's **Pages** tab and return the link to the supervisor (see [Pages tab](#pages-tab)).
4. If upload, access verification or rendering fails, preserve the Drive output and report the Pages issue. Never weaken Access to make a link work. A revised Stage 4 artifact may redeploy the same branch after checking the new source and assets; keep the earlier Drive artifact and Document Index history intact.

## Pages tab

The Document Index workbook's **Pages** tab lists every published page so the founder can find it without asking an agent or opening Cloudflare. After a verified publish (step 3), map the tab's columns by header name and write one row per page address:

| Column | Value |
| --- | --- |
| Pipeline ID | The item the page was published for |
| Document ID | The Drive artifact's Document ID; blank if the page has no Document Index row |
| Title | The Document Index title, or a short name for the page |
| Description | One or two sentences on what the page shows |
| URL | The exact `url` the publish result returned, never one built by hand |
| Published | Date of this deployment, `DD/MM/YYYY` |
| Run ID | This run's ID; blank outside a run |

Find an existing row by URL, never by position. A redeploy to the same address updates that row's Document ID, Title, Description, Published and Run ID; a new address gets a new row. Never write a row for a publish that failed or wasn't verified, and leave other rows alone.

Cloudflare references: [Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/), [preview aliases and access](https://developers.cloudflare.com/pages/configuration/preview-deployments/), and [protecting the main Pages hostname](https://developers.cloudflare.com/pages/platform/known-issues/#enable-access-on-your-pagesdev-domain).
