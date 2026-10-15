# MCP next steps

Date: 2026-10-12. Initial review; recommendations are not approved implementation decisions.

## Question

Which pending MCP tasks can be tackled first, and what depends on other decisions?

## Verified findings

- Cloud Build pins Trivy 0.75.0 in all five scanner steps. The official latest release is also 0.75.0 as checked today; no version upgrade is presently available. Existing release gates passed previously, but were not rerun in this review.
- Agent Register MCP IDs 8–9 describe implemented but cloud-disabled Google reads. IDs 10–13 require new Google write/workflow operations. Identity OAuth currently does not authorize Drive access.
- IDs 1–6 cover unimplemented Alexandria discovery, Shopify, Alibaba and trends. IDs 17–18 cover disabled advanced Tavily and optional extraction. IDs 21–23 cover planning-note writes and future DataForSEO. These have different permissions and pricing requirements; enabling them together is not a small change.
- Document graph registers both read and write/embedding tools in one server. Its source has no client-specific authorization or resource filtering. Cloud Run IAM protects the cloud service; publishing it alone would not provide restricted client permissions.
- Document queries currently store title/content/type/agent/supersedes, without a Drive file identity, Document Index ID or revision fingerprint. Graph writes are not an idempotent index synchronization interface.
- Prompt paths now reside under personas/subscriptions/. Clickable GitHub links depend on publishing these files; the existing no-push instruction remains in force.

## Recommended sequence

1. Finish this capability inventory and settle document-graph access and index metadata before adding tools.
2. Review current deployed-image findings against a fresh vulnerability database. A rebuild with --pull can pick up base updates; scans of the deployed digest and scans of a newly built candidate answer different questions. Keep report-unfixed/block-fixable policy. Do not claim yesterday's findings are still unfixed without a fresh scan.
3. Enable scoped Google reads first if gateway-based Drive access is needed; retain native Google plugin access meanwhile. Start with approved IDs/folders and a dedicated provider authorization flow. Implement Google writes only after idempotent creation, revision checks and register ID allocation/claim rules are designed.
4. Start external document-graph access with read-only gateway adapters to the separate private service. Retain that service's IAM check; authorize only the gateway service identity as invoker. Gateway OAuth provides client identity, with explicit document scope and bounded results enforced server-side. Give Hermes a separate authenticated writer path. Embedding/write calls need distinct permission and cost limits.
5. Choose the actual scheduled runtime before testing unattended access. Verify native connection availability, refresh after access-token expiry, timeout behavior and reconnect failures. Then issue server-owned run assignments with fresh limits under the persistent login; clients must not be able to mint their own quota resets.
6. Publish prompt files and add verified GitHub links when the operator requests a push.

## Proposed Document Index extension

Inspect live Document Index headers and revision conventions before making any sheet changes. Initial proposal: one operator-controlled Graph inclusion field (Include / Exclude; default Exclude), plus machine-maintained Graph sync status, Graph document ID, Graph synced revision and Graph last synced at. Keep detailed failures in logs with a safe correlation reference. These are proposals, not added columns.

A graph source record should retain source system, stable Drive file ID, permanent Document Index ID, Pipeline ID, domain/entity, revision identity or content hash, source URL, source timestamp, document type, and supersedes mapping. Use an idempotent source identity/revision key so retries cannot duplicate documents. Sheet inclusion is indexing intent, not access authorization; excluded content must not be embedded. Define removal behavior explicitly: exclusion should immediately prevent serving indexed content, with deletion/retention decided separately. Drive/Sheets remain authoritative for subscription outputs; indexing copies selected content.

## Open decisions

- Which external clients need graph reads, and which need writes? Which document domains may each read?
- Should initial provider work prioritize Google reads, trends or product discovery?
- Is manual inclusion sufficient, and should graph copies preserve full content or only selected evidence?
- Which scheduled platform/runtime will be tested first?

## Sources

- Live Welladino — Agent Register MCP tab, inspected 2026-10-12.
- cloudbuild.yaml; mcp-servers/document-graph/server.py; document_graph/tools.py; document_graph/integrations/neon/client.py.
- Official Trivy release: https://github.com/aquasecurity/trivy/releases/tag/v0.75.0

No cloud changes, paid calls, new credentials, provider enablement or push were performed for this review.

## Operator sequencing update

The operator selected provider expansion first (excluding DataForSEO), followed by unattended runtime verification and identity/run quota separation. Document-graph access/indexing will be revisited afterward. Google work and GitHub planning-note writer activation were then deferred explicitly. See [read capability implementation note](../notes/2026-10-12_gateway-provider-scope_note.md). Existing Document Index graph fields were found during scoped live inspection; no new columns were added, and their behavior remains deferred.
