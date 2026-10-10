# Subscription-agent skill source and documentation

Moved the three Welladino skills into `subscription-agents/skills/`, retaining compatibility symlinks at the old shared location. Refreshed local Codex copies. Corrected removed Pipeline link fields, numeric register IDs, Agent type/Manual selection and document revision linking.

Added standing architecture and an operational runbook for the document-driven secondary workflow. Scoped Hermes output rules separately and corrected the stale Supabase reference to Neon. No Apps Script source, credentials, online project, Drive documents or schedules changed. The published workflow plugin still requires a release from the updated source; its cache was not modified.

Verification: manual skill frontmatter checks, local reference checks, source/installed comparison and existing offline ClickUp sync tests. No live sync or AI schedule was run.

The bundled skill validator could not run because PyYAML is unavailable in the inspected Python runtimes. No dependencies were installed.
