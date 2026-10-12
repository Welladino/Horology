# Private test clients and runtime policies

Moved ignored local/cloud manual-test client JSON files from gateway config into `tests/mcp_servers/gateway/fixtures/private/`. Preserved credentials and mode 0600. Updated local setup/smoke paths; ignored all private fixture files and explicitly excluded the directory from Cloud Build source uploads. No credentials were printed, rotated or published.

Runtime policies remain in gateway config: the example is tracked, local/cloud variants are private operator inputs. Local Compose mounts local policy. Cloud Run loads its versioned Secret Manager policy at `/config/policy.json`; it does not read ignored laptop files.

Psycopg 2 was retained because Supabase metadata, document-graph and Alembic/CI still require it. Removing the package safely needs a separate migration of those consumers. No Cloud Build/deployment/commit performed for this cleanup.
