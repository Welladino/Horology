# Deploy the MCP services to Cloud Run

How the pieces fit: [Cloud architecture](../../architecture/cloud/README.md) and [MCP services](../../architecture/mcp/README.md). Building images: [Cloud Build](cloud_build.md). Profiles, post-deploy checks and build lookups: [operator access and checks](operator_checks.md). Why things are set up this way: the [notes index](../../planning/notes/index/HOROLOGY_NOTES_INDEX.md).

Project `horology-dev`, region `us-central1`, registry `us-central1-docker.pkg.dev/horology-dev/mcp-servers`. Pass `--project` and `--region` on every command.

## Who runs what

| Action | Configuration |
|---|---|
| Submit builds, update the `mcp-gateway` and `document-graph` services, tag images | `horology` (impersonates `horology-deployer`) |
| Anything on the `document-graph-sync` job, service ingress or IAM, secrets, APIs | `horology-admin` |

The deployer deliberately can't touch the job, IAM or secrets (decided 2026-10-13).

## Current configuration

Both services: 1 CPU, 512 MiB, concurrency 4, at most 1 instance, minimum 0, request-based billing, 60-second timeout, invoker IAM check off (every MCP tool needs Google sign-in).

| Service | Secrets (pinned version) | Plain settings |
|---|---|---|
| `mcp-gateway` (runs as `mcp-gateway@`) | `GATEWAY_DATABASE_URL` = `horology-gateway-db:1`, `TAVILY_API_KEY` = `horology-gateway-tavily:1`, `FIRECRAWL_API_KEY` = `horology-gateway-firecrawl:1`, `SUPABASE_METADATA_DSN` = `horology-gateway-supabase:1`, `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` = `horology-gateway-google-client-id:1` / `-secret:1` | `GATEWAY_OAUTH_ENABLED=true`, `GATEWAY_PUBLIC_URL` (service base URL, no `/mcp`). Policy is baked into the image. |
| `document-graph` (runs as `document-graph@`) | `DATABASE_URL_POOLED` = `horology-graph-db:2`, `OPENROUTER_API_KEY` = `horology-graph-openrouter:2`, `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` = `horology-graph-google-client-id:1` / `-secret:1` | `DOCUMENT_GRAPH_OAUTH_ENABLED=true`, `DOCUMENT_GRAPH_PUBLIC_URL`, `DOCUMENT_GRAPH_WORKSPACES` (email → workspace JSON), `GRAPH_SYNC_JOB` |
| `document-graph-sync` job (runs as `document-graph-sync@`) | `DATABASE_URL_POOLED` = `horology-graph-db:2`, `OPENROUTER_API_KEY` = `horology-graph-openrouter:2` | `GRAPH_SYNC_WORKBOOKS` (workspace → Document Index id JSON), `GRAPH_SYNC_JOB`; command `python -m graph_sync`, 60-minute task limit, no retries |

Both services share one Google OAuth client, so one Audience test-user list covers both. Its redirect URIs are `https://mcp-gateway-366292507424.us-central1.run.app/auth/google/callback` and `https://document-graph-366292507424.us-central1.run.app/auth/google/callback`.

Never put secret values in tracked files, command arguments or logs. Each runtime identity reads only its own secrets.

## Release

1. **Build** through [Cloud Build](cloud_build.md) and note both image digests.
2. **Migrate first**, if the release adds Alembic revisions, with the owner `DATABASE_URL` in the root `.env` ([Alembic workflow](../db/alembic_workflow.md)). Check the migration is safe for the revisions still running; if it isn't, run steps 2 and 3 back to back.

```bash
.venv/bin/dotenv -f .env run -- .venv/bin/python -m alembic upgrade head
```

3. **Record the serving revisions** for rollback:

```bash
gcloud --configuration=horology run services list --project=horology-dev --region=us-central1
```

4. **Deploy the gateway.** Replace `DIGEST`:

```bash
gcloud --configuration=horology run services update mcp-gateway --project=horology-dev --region=us-central1 --image=us-central1-docker.pkg.dev/horology-dev/mcp-servers/mcp-gateway@sha256:DIGEST
```

5. **Deploy the document graph**, service then job, with the same digest:

```bash
gcloud --configuration=horology run services update document-graph --project=horology-dev --region=us-central1 --image=us-central1-docker.pkg.dev/horology-dev/mcp-servers/document-graph@sha256:DIGEST
```

```bash
gcloud --configuration=horology-admin run jobs update document-graph-sync --project=horology-dev --region=us-central1 --image=us-central1-docker.pkg.dev/horology-dev/mcp-servers/document-graph@sha256:DIGEST
```

6. **Verify** with the [post-deploy checks](operator_checks.md#after-a-deploy), then `gateway_status` and `list_documents` from a connected client. Compare latency with the baseline: `scripts/ops/live_check.py`.
7. **Protect the deployed images** by moving `deployed-current` ([Cloud Build](cloud_build.md)).

## Roll back

Send traffic to an earlier verified revision. Rollback doesn't undo migrations or reset usage.

```bash
gcloud --configuration=horology run services update-traffic mcp-gateway --project=horology-dev --region=us-central1 --to-revisions=VERIFIED_REVISION=100
```

Revisions that can't be rolled back to, because they read secrets or columns that no longer exist: `mcp-gateway` before `00009`, `document-graph` before `00003`. If a lasting rollback uses an older image, give its digest a `deployed-` tag so clean-up keeps it.

## Rotate a secret

Add a version, move every user of the secret to it, then disable the old version. A service pinned to a destroyed version can't start new instances. For the graph's OpenRouter key, both the service and the job use it:

```bash
gcloud --configuration=horology-admin secrets versions add horology-graph-openrouter --project=horology-dev --data-file=-
```

```bash
gcloud --configuration=horology run services update document-graph --project=horology-dev --region=us-central1 --update-secrets=OPENROUTER_API_KEY=horology-graph-openrouter:NEW_VERSION
```

```bash
gcloud --configuration=horology-admin run jobs update document-graph-sync --project=horology-dev --region=us-central1 --update-secrets=OPENROUTER_API_KEY=horology-graph-openrouter:NEW_VERSION
```

## Run the sync job by hand

Agents normally start it with `sync_graph`. By hand, for every workspace:

```bash
gcloud --configuration=horology-admin run jobs execute document-graph-sync --project=horology-dev --region=us-central1 --wait
```

Only entity extraction, or only rebuilding topics:

```bash
gcloud --configuration=horology-admin run jobs execute document-graph-sync --project=horology-dev --region=us-central1 --update-env-vars=GRAPH_SYNC_MODE=entities
```

```bash
gcloud --configuration=horology-admin run jobs execute document-graph-sync --project=horology-dev --region=us-central1 --update-env-vars=GRAPH_SYNC_MODE=topics
```

Results land in the Document Index (Graph Sync Status, and the Entities and Entity types tabs), not in the command output. A run handles 30 documents and starts the next run itself, at most 10 in a row.

## Add a workspace

1. Copy the Document Index workbook for the new workspace.
2. In Drive, share the workbook with `document-graph-sync@horology-dev.iam.gserviceaccount.com` as **Editor** (it writes status back) and each folder holding indexed documents as **Viewer**.
3. Add the workbook to `GRAPH_SYNC_WORKBOOKS` on the job (`horology-admin`), and the person's email to `DOCUMENT_GRAPH_WORKSPACES` on the service. Both are JSON, so use gcloud's `^|^` separator prefix, for example `--update-env-vars='^|^GRAPH_SYNC_WORKBOOKS={"welladino":"…","other":"…"}'`.

## Add or remove a person

Add: Google Auth Platform → Audience (`horology-dev`) → Test users → **Add users**. Keep publishing status **Testing**. For the document graph, also map their email in `DOCUMENT_GRAPH_WORKSPACES`.

Remove:

1. Delete them from Audience test users, so they can't sign in again.
2. Revoke their gateway tokens, with the gateway's private `GATEWAY_DATABASE_URL`:

```bash
set -a; . mcp-servers/mcp-gateway/.env.local; set +a; .venv/bin/python mcp-servers/mcp-gateway/scripts/revoke_email.py person@example.com
```

3. Remove their email from `DOCUMENT_GRAPH_WORKSPACES`; an unmapped email can't use a document-graph token.

Clients stop working within 5 minutes, when the in-memory token cache expires; deploying a new revision cuts them off at once. Grants issued before 2026-10-13 carry no email and can't be matched.

## One-time setup (already done)

Kept so the environment can be rebuilt. APIs enabled: Cloud Run, Artifact Registry, Secret Manager, IAM, Sheets, Drive.

Job identity and its secrets:

```bash
gcloud --configuration=horology-admin iam service-accounts create document-graph-sync --project=horology-dev --display-name="Document graph sheet sync"
```

```bash
for secret in horology-graph-db horology-graph-openrouter; do gcloud --configuration=horology-admin secrets add-iam-policy-binding "$secret" --project=horology-dev --member=serviceAccount:document-graph-sync@horology-dev.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor; done
```

The job (replace `DIGEST`):

```bash
gcloud --configuration=horology-admin run jobs create document-graph-sync --project=horology-dev --region=us-central1 --image=us-central1-docker.pkg.dev/horology-dev/mcp-servers/document-graph@sha256:DIGEST --command=python --args=-m,graph_sync --service-account=document-graph-sync@horology-dev.iam.gserviceaccount.com --set-secrets=DATABASE_URL_POOLED=horology-graph-db:2,OPENROUTER_API_KEY=horology-graph-openrouter:2 --set-env-vars='^|^GRAPH_SYNC_WORKBOOKS={"welladino":"1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc"}|GRAPH_SYNC_JOB=projects/horology-dev/locations/us-central1/jobs/document-graph-sync' --max-retries=0 --task-timeout=3600s
```

Who may start it (the service, and the job itself for follow-up runs):

```bash
for sa in document-graph document-graph-sync; do gcloud --configuration=horology-admin run jobs add-iam-policy-binding document-graph-sync --project=horology-dev --region=us-central1 --member=serviceAccount:$sa@horology-dev.iam.gserviceaccount.com --role=roles/run.jobsExecutorWithOverrides; done
```

Public ingress with application sign-in, per service (an organisation policy forbids `allUsers` invoker bindings):

```bash
gcloud --configuration=horology-admin run services update document-graph --project=horology-dev --region=us-central1 --no-invoker-iam-check
```

Reverse with `--invoker-iam-check` before rolling back to any revision without sign-in. The `_Default` logging sink keeps the exclusion `horology-oauth-query-privacy` for `/auth/` and `/authorize` URLs; copy it to any new request-log sink.
