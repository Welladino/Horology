# Repository organization — 2026-10-12

Workflow skill sources now live in `plugins/welladino-workflows/skills/`, together with the existing plugin identity, manifests and referenced icon. Horology MCP instructions remain under `plugins/horology/`. Subscription-agent personas remain under `personas/subscriptions/`.

Renamed the Apps Script source root to `google_appscript/`; ClickUp sync remains its own component at `google_appscript/clickup-sync/`. Active documentation and command references were updated; historical planning records retain their original paths.

Gateway tests were consolidated under `tests/mcp_servers/gateway/`; CI discovers the root `tests/` tree. Generated shared-runtime egg-info directories were removed and ignored. Local gateway helper and integration file names were clarified. No publishing, commit or deployment was performed by this organization change.
