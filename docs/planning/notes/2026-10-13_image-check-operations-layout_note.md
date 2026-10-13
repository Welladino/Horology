# Image checks and GCP operations configuration

The image-contract script executes inside the gateway or document-graph image, where the server packages live under /app. Local editor imports from scripts/ci cannot resolve that layout. Use explicit importlib runtime imports and required-symbol lookups; missing packages or symbols still fail the image check. No type-checker suppression or sys.path mutation was added to the production check.

Moved the unchanged Artifact Registry cleanup policy from scripts/ci/artifact-cleanup.json to ops/gcp/artifact-cleanup.json and updated the active release runbook. This is operator-applied GCP configuration, not a build step. No cleanup policy was applied.

Migration 20261013_001 creates no tables: it renames historical assignment columns/indexes to client_id, preserving all existing rows. It remains pending for the production rollout; old/new gateway revisions need coordination around the rename.

No migration, Cloud Build, deployment, plugin publication, scheduled test or register update performed.
