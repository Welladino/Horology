# Gateway integration modularization

Split gateway/providers.py into provider packages under gateway/integrations: github, supabase, tavily, firecrawl and google_drive. Removed the old monolithic module and updated server imports and existing test mock targets. Shared bounded HTTP and text masking moved into gateway/shared/http.py and text.py. Authentication, assignment authorization, quotas and the existing SQLite ledger remain central and unchanged. One Docker image and endpoint remain.

Updated the Docker build allowlist for nested Python packages while retaining exclusions for credentials and local policy. Public Supabase CA packaging remains unchanged. Google OAuth and cloud deployment remain deferred.

Validation: 16 existing regression tests passed, Docker build succeeded, and the rebuilt running container passed authenticated MCP handshake, discovery of all thirteen tools, invalid-auth rejection and scope denial. No paid or live provider calls were needed for this refactor, and existing quota state was preserved.
