# Deploy the MCP services to Cloud Run

Start with [MCP operations: how the pieces connect](../architecture/mcp_operations.md) for diagrams, identities, security checks and client access.

Status: Google-backed gateway OAuth deployed and private cloud checks verified on 2026-10-11. Eleven secrets exist. Public gateway ingress is enabled and unauthenticated tools are rejected; native browser login remains pending. Document graph remains IAM-private.

## Target

Project `horology-dev`, region `us-central1`, Artifact Registry repository `mcp-servers`. Service names `mcp-gateway` and `document-graph`. Use explicit project/region flags on every cloud command. Deploy private first. Gateway OAuth clients need externally reachable discovery/sign-in routes; granting allUsers gateway invocation requires the operator’s explicit approval. Keep document graph IAM-private.

## Prerequisites

Cloud Run (`run.googleapis.com`), Artifact Registry (`artifactregistry.googleapis.com`), Secret Manager (`secretmanager.googleapis.com`) and IAM (`iam.googleapis.com`) must be enabled. All four were enabled by the operator and verified on 2026-10-11. Local Docker builds do not need Cloud Build. No APIs were enabled by the preparation work.

## Images

From the repository root:

```sh
docker buildx build --platform linux/amd64 --load -t horology-mcp-gateway:cloud -f mcp-servers/mcp-gateway/Dockerfile .
docker buildx build --platform linux/amd64 --load -t horology-document-graph:cloud -f mcp-servers/document-graph/Dockerfile .
```

The root build allowlist packages shared-runtime and the gateway public CA, excluding private env/config files. The repository now exists and the initial tested images are uploaded. Use the Horology gcloud configuration for registry authentication on future uploads. Tag each image with a unique release tag; deploy the resulting digest.

## Runtime settings and secrets

Both servers read Cloud Run's PORT and use stateless JSON MCP requests. Existing local ports remain 8767 and 8765. No persistent container filesystem is needed.

| Service | Secret Manager input | Private local source |
| --- | --- | --- |
| gateway | GATEWAY_DATABASE_URL | gateway .env.local |
| gateway | TAVILY_API_KEY, FIRECRAWL_API_KEY, SUPABASE_METADATA_DSN | gateway .env.local |
| gateway | GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET | Google Auth Platform client |
| gateway (no secret) | policy at /config/policy.json, baked into the image | tracked `mcp-servers/mcp-gateway/config/policy.cloud.json` |
| document graph | DATABASE_URL_POOLED, OPENROUTER_API_KEY | document-graph .env |

Google sign-in credentials now exist in service-specific Secret Manager secrets; Google Drive provider credentials remain absent. Never place secret values in tracked files, command arguments, logs or container layers. Pin deployed secret versions instead of silently relying on latest. Give each runtime identity secretAccessor on its own secrets only. A gateway credential never needs access to document-graph DB/OpenRouter secrets.

Set GATEWAY_PUBLIC_URL to the actual HTTPS Cloud Run service base URL, without /mcp. Auth metadata uses this base URL and its /mcp endpoint. A private initial revision may start using the local metadata default while discovering the service URL; immediately update GATEWAY_PUBLIC_URL and verify the revised metadata before client testing. With GATEWAY_OAUTH_ENABLED=true, the gateway publishes authorization-server discovery as well as protected-resource metadata.

## First deployment settings

Use --no-allow-unauthenticated, --min-instances=0, --max-instances=1, --concurrency=4, --cpu=1, --memory=512Mi, --port=8080, --timeout=60 and request-based billing (--cpu-throttling). These are initial operating limits, not a spending cap. Neon reservations remain atomic even if revisions overlap. Choose a billing alert amount with the operator.

Cloud Run IAM protects document graph until application/client authentication is implemented. The gateway also retains assignment-bearer authorization. A test client for the gateway sends its Cloud Run identity token in X-Serverless-Authorization and its assignment bearer in Authorization; document graph needs only Cloud Run authentication. Do not expose document graph publicly to simplify testing.

Initial deployment uses these concrete resources (all secret versions are 1):

- Gateway identity: mcp-gateway@horology-dev.iam.gserviceaccount.com.
- Document-graph identity: document-graph@horology-dev.iam.gserviceaccount.com.
- Gateway image: us-central1-docker.pkg.dev/horology-dev/mcp-servers/mcp-gateway@sha256:a751997a7dfe8e47a3079d443ed2769e9bafd574be8a1430d61aef157c55a029.
- Graph image: us-central1-docker.pkg.dev/horology-dev/mcp-servers/document-graph@sha256:ad8b516cc09877d7ed9936cb2a8d981fd282fabcd2ea1bd1ab45a2a71e79bdb0.

Gateway secret mappings: GATEWAY_DATABASE_URL=horology-gateway-db:1, GITHUB_TOKEN=horology-gateway-github:1, TAVILY_API_KEY=horology-gateway-tavily:1, FIRECRAWL_API_KEY=horology-gateway-firecrawl:1, SUPABASE_METADATA_DSN=horology-gateway-supabase:1, GATEWAY_TOKEN_HASHES=horology-gateway-token-hashes:1, /config/policy.json=horology-gateway-policy:1.
Graph mappings: DATABASE_URL_POOLED=horology-graph-db:1, OPENROUTER_API_KEY=horology-graph-openrouter:1.

## Verified endpoints and revisions

- Gateway: https://mcp-gateway-366292507424.us-central1.run.app/mcp; current OAuth revision mcp-gateway-00004-25t. Initial static-token revision mcp-gateway-00002-df9 remains a rollback reference.
- Document graph: https://document-graph-366292507424.us-central1.run.app/mcp; revision document-graph-00001-k69.
- Cloud Run also advertises legacy hashed service URL aliases. Gateway auth metadata uses the verified endpoint above.
- Both services have no service-level invoker bindings; callers need inherited project permission or an explicit later invoker grant. Neither has allUsers access.

The historical private cloud test client file is now tests/mcp_servers/gateway/fixtures/private/client.cloud.json, ignored by Git and excluded from source uploads. It contains the assignment bearer only; a compatible test client must obtain a fresh Cloud Run identity token separately. The initial cloud assignment expires 24 hours after provisioning. Do not extend or reuse run IDs to reset counters. Generate a fresh operator-approved assignment for each future run, update versioned policy/token mappings and retain shared quota history.

## Inspect and roll back

```sh
gcloud --configuration=horology run services describe mcp-gateway --project=horology-dev --region=us-central1
gcloud --configuration=horology run services describe document-graph --project=horology-dev --region=us-central1
# Replace the revision placeholder with a previously verified revision:
gcloud --configuration=horology run services update-traffic mcp-gateway --project=horology-dev --region=us-central1 --to-revisions=VERIFIED_REVISION=100
```

For a future deployment use `gcloud --configuration=horology run deploy SERVICE`, specifying the target project/region, pinned image, corresponding runtime identity and secret mapping above, and the first deployment settings. Retain GATEWAY_PUBLIC_URL on gateway revisions. Never dump secret values to diagnose a deployment.

## Validation and rollback

Verify unauthenticated requests fail at ingress; then test MCP initialization, tools and denied scopes with the compatible authenticated client. Check metadata URLs, quota totals across service restarts, safe errors and JSON operation logs. Keep paid calls minimal. Document graph writes/embeddings remain deferred until its cloud access and usage limits are verified. Record image digest, revision, URLs and secret version numbers without values.

Before updating an existing service, record the current revision. Rollback sends traffic to the prior verified revision; it does not downgrade the Neon quota schema or reset usage history.

Sources: [container contract](https://docs.cloud.google.com/run/docs/container-contract), [service authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).

## OAuth revision

Gateway image: `us-central1-docker.pkg.dev/horology-dev/mcp-servers/mcp-gateway@sha256:2bb10839baf17a5cb93001a594c80bfadbdafa92efa85fcd30f6498cc31f4f71`, tag `20261011-oauth-2`, revision `mcp-gateway-00004-25t`.

Additional mappings: GOOGLE_OAUTH_CLIENT_ID=horology-gateway-google-client-id:1 and GOOGLE_OAUTH_CLIENT_SECRET=horology-gateway-google-client-secret:1. Policy is now horology-gateway-policy:2. GATEWAY_OAUTH_ENABLED=true; approved email-to-assignment mapping is configured in GATEWAY_OAUTH_ASSIGNMENTS. The owner-interactive assignment is independently provisioned for 30 days and retains all existing caps; the previous cloud-smoke expiry is unchanged.

Google callback: `https://mcp-gateway-366292507424.us-central1.run.app/auth/google/callback`. MCP clients register with the gateway, not with Google. The gateway alone holds the Google client secret. Google only supplies identity, not Drive access.

Alembic revision 20261011_002 persists OAuth clients, login state and grants in gateway_auth. See the [OAuth note](../../planning/notes/2026-10-11_gateway-oauth_note.md) for credential storage, scopes, expiry and validation.

The application omits Uvicorn access logs. The `_Default` Logging sink has exclusion `horology-oauth-query-privacy` for gateway `/auth/` and `/authorize` request URLs; all other tool/request/error and required audit logging remains. Preserve this exclusion and copy it to any future custom request-log sink.

Private cloud smoke verified discovery, DCR, Google redirect, callback CSRF rejection and 17-tool initialization using the existing assignment bearer. Seventy-six regression tests passed. No paid upstream calls were made.

External ingress is currently pending: automatic approval review rejected granting `allUsers` `roles/run.invoker` because the earlier setup authorization did not explicitly cover public IAM exposure. The operator has been asked to approve that exact gateway-only change. No public binding was applied. Native Codex login remains pending the ingress decision and operator browser sign-in. Document graph has no public invoker binding.

If external ingress is approved, grant gateway invocation, verify anonymous `/mcp` returns 401 and document graph remains inaccessible, then connect Codex using DCR and complete the Google browser flow. If ingress remains private, a compatible client needs Cloud Run identity headers in addition to OAuth; standard remote clients cannot be assumed to supply them.

Rollback from externally accessible OAuth must restore private ingress before reverting to an older revision. Do not leave an old static-token revision publicly reachable by accident. Preserve quota and OAuth schema/history during rollback.

### Public ingress decision update

The operator approved option 1 (externally reachable gateway protected by OAuth). Applying an allUsers Cloud Run Invoker binding failed with GCP FAILED_PRECONDITION because of an organization policy restricting permitted IAM members. No binding was applied.

Google's documented alternative is a service-level `--no-invoker-iam-check` update on mcp-gateway only. Automatic approval review rejected this fallback because the transcript did not explicitly authorize that distinct setting. The gateway remains IAM-private, and native OAuth login cannot yet reach discovery publicly. Document graph is unchanged. Await explicit approval for disabling the gateway's invoker IAM check; do not alter organization policies.

Reference: [Cloud Run public access](https://docs.cloud.google.com/run/docs/authenticating/public). Restore `--invoker-iam-check` to reverse this service-level setting if it is later enabled.

### Public gateway enabled

The operator explicitly approved disabling the invoker IAM check on mcp-gateway only. Applied `--no-invoker-iam-check` to horology-dev/us-central1 on 2026-10-11; service annotation `run.googleapis.com/invoker-iam-disabled=true`. Revision remains mcp-gateway-00004-25t. No organization policy or document-graph setting was changed.

External checks passed: OAuth discovery 200; anonymous and invalid-bearer `/mcp` requests 401; document graph anonymous request 403. Codex DCR login initiated and browser sign-in is pending. Reverse gateway public ingress with `--invoker-iam-check` before rolling back to a revision that lacks OAuth protection.

### Consent CSP release

Deployed revision mcp-gateway-00005-wjd, tag 20261011-oauth-csp-1, digest sha256:9f9eb79e1ed223ec904d738aa737248f105edbb25e2ac6bf4558bcd8750162c6. Consent-page form-action now permits the validated client's exact callback origin and port so Chrome can follow the final OAuth redirect. Discovery and auth boundary checks passed after deployment. Browser verification is pending a fresh login; do not reuse a consumed consent page. See [fix note](../../planning/notes/2026-10-11_oauth-consent-csp-fix_note.md).

### Native Codex OAuth completed

On 2026-10-12 the operator completed Google sign-in and gateway consent. Codex CLI confirmed `Successfully logged in to MCP server 'horology'`; `codex mcp list` reports horology enabled with OAuth. The consent CSP fix is verified by this completed browser flow. The existing chat has not reloaded its native tool catalog, so direct OAuth-authenticated tool invocation in this chat remains pending a fresh connection. No paid tools were called during login verification.

### One-page warm Firecrawl timing test

On 2026-10-12, the operator requested a fresh scrape of a different page. Approved https://example.com/ in the global Firecrawl URL policy and owner-interactive assignment without changing limits or expiry. Policy Secret Manager version is now 3; current revision mcp-gateway-00006-wf2 uses the same image digest as the consent CSP release. No application code changed for this test.

After a successful gateway_status warm-up, the native scrape took 13.554 seconds as observed from the assistant and 9.098 seconds inside the handler. It returned 959 markdown characters. Instance-start logs precede the measured call; no new instance-start event occurred during it. The preceding Forbes test took 32.342 seconds including an instance startup and OAuth token renewal, with 9.487 seconds inside its handler. These are single samples from different pages, not a controlled estimate of cold-start savings. Provider, database, auth and client overhead are not fully separated.

## Current release path (2026-10-12)

Use [Cloud Build release instructions](cloud_build.md) instead of producing locally versioned release images. Both services now use images built and scanned by the root `cloudbuild.yaml` pipeline in `us-central1`.

- Gateway: `mcp-gateway-00007-r2c`, image digest `sha256:faf5e1ef426684baa4bbb4bbe6468643082f9291c3eca2a2cd971a9c7a885ef5`.
- Document graph: `document-graph-00002-rks`, image digest `sha256:81c61b59660cb8e59a96ed22a35a2d6b208d2332c90cf6bbd859729e267f7d9f`.
- Artifact Registry cleanup: five recent versions per package plus protected `deployed-` tags. Both current images have `deployed-current`.
- Build account: `mcp-build@horology-dev.iam.gserviceaccount.com`; repository writer, project log writer, source-bucket object viewer. No provider-secret or deployment permissions.

Rollback to the previous gateway revision while its image remains retained:

```bash
gcloud --configuration=horology run services update-traffic mcp-gateway --project=horology-dev --region=us-central1 --to-revisions=mcp-gateway-00006-wf2=100
```

If using an older revision for a lasting rollback, move `deployed-current` to its digest before cleanup can remove it. Preserve intentional rollback digests with `deployed-` tags when older than five versions.

## Next gateway release: shared access policy (prepared 2026-10-13, deployed 2026-10-13 as mcp-gateway-00009-8hr)

Revision `mcp-gateway-00008-kqw` still runs the old assignment-based image. The new image needs these changes in this order; skipping one stops the new revision from starting or lets nobody sign in. Why: [remove assignments](../../planning/notes/2026-10-13_remove-assignments_note.md), [Audience sign-in and baked policy](../../planning/notes/2026-10-13_audience-signin-baked-policy_note.md).

1. In Google Auth Platform → Audience for `horology-dev`, confirm the app is External, status Testing, and every person who should connect is a test user.
2. Build through [Cloud Build](cloud_build.md) and note the gateway image digest.
3. Apply the column-rename migration with the direct owner `DATABASE_URL` (see [Alembic workflow](../db/alembic_workflow.md)):

```bash
.venv/bin/alembic upgrade head
```

From this step until step 4 finishes, the old revision's quota and cache queries fail, because it expects the old column names. Run steps 3 and 4 back to back.

4. Deploy that digest, dropping the old settings. Replace `DIGEST`:

```bash
gcloud --configuration=horology run services update mcp-gateway --project=horology-dev --region=us-central1 --image=us-central1-docker.pkg.dev/horology-dev/mcp-servers/mcp-gateway@sha256:DIGEST --remove-env-vars=GATEWAY_OAUTH_ASSIGNMENTS --remove-secrets=GITHUB_TOKEN,GATEWAY_TOKEN_HASHES --clear-volume-mounts --clear-volumes
```

`--clear-volumes` removes both policy secret volumes (versions 3 and 4); the policy now comes from the image. Removing `GATEWAY_TOKEN_HASHES` makes the cloud OAuth-only; local Compose and Hermes keep bearer tokens.

5. Verify: unauthenticated `/mcp` returns 401, a test user can sign in from a client, `gateway_status` lists the tools in `policy.cloud.json` and none starting with `github_` or `drive_`, and a non-test-user Google account is refused at Google sign-in.
6. After the release has run cleanly for a while, disable (do not delete) secret versions `horology-gateway-policy`, `horology-gateway-github` and `horology-gateway-token-hashes`, and the ignored local `policy.cloud.secret-v4.local.json` snapshot can go.

Rollback: route traffic back to `mcp-gateway-00008-kqw`. The rename migration must be reverted first, because the old image expects the old column names; do not downgrade while the new revision serves traffic.

## Document graph sign-in and sheet sync release (prepared 2026-10-13, partly run)

Progress 2026-10-13, from Cloud Build `d7ed4029-3498-4d0e-991d-f2bc3e6cce72` (gateway `sha256:e8747865707adfc13058d92c121ff01a84a7d12924c750922ba892482a532356`, document-graph `sha256:4a9bebc118984b02cfed82be4613e7f74a9abff5b723ce50685d33746b41f254`):

- Done: steps 1–4, 6, 7, 9, 10 and 11. `horology-graph-db:2` added; Sheets and Drive APIs enabled; `document-graph-sync` identity created and allowed its two secrets; job `document-graph-sync` created; `document-graph` allowed to start it with overrides; `horology-graph-google-client-id`/`-secret` created by the operator; revision `document-graph-00003-7cv` serves with sign-in on, `horology-graph-db:2` and the map `saravanaraj.subramaniam@welladino.com` → `welladino`. It started cleanly; the invoker check is still on, so it could not be tested from outside.
- Open: step 5 (Drive sharing, operator), the redirect URI in step 10 (operator, console), step 8 (manual job run, after sharing), step 12 (invoker check off, needs approval) and step 13.
- `horology-deployer` cannot create jobs (`run.jobs.create` denied); the job was created with `--configuration=horology-admin`. Check whether it may update the job's image on later releases.
- The gateway's own release (section above) ran at the same time: revision `mcp-gateway-00009-8hr`, without `GATEWAY_OAUTH_ASSIGNMENTS`, `GITHUB_TOKEN`, `GATEWAY_TOKEN_HASHES` or policy volumes. Anonymous `/mcp` returns 401 and discovery 200.


Puts document-graph on Google sign-in (second connector), moves it to the `horology_graph` login, and adds the `document-graph-sync` job. Why: [document-graph plan](../../planning/notes/2026-10-13_document-graph-sheet-controlled-access_note.md), [sign-in and sync note](../../planning/notes/2026-10-13_document-graph-signin-and-sheet-sync_note.md). Run the steps in order; steps marked **approval** change access and need the operator's explicit go-ahead.

1. Done 2026-10-13. Migration `20261013_003` was applied to Neon with a generated `GRAPH_DB_PASSWORD` (kept in the root `.env`, next to `GATEWAY_DB_PASSWORD`). The local `mcp-servers/document-graph/.env` now uses `horology_graph`. A check confirmed the login reads the graph and is refused on gateway tables and on `CREATE TABLE`.

2. Add a new version of the document-graph database secret from the local `.env` value (the pooled URL with `horology_graph`). Nothing is printed:

```bash
.venv/bin/dotenv -f mcp-servers/document-graph/.env run -- sh -c 'printf %s "$DATABASE_URL_POOLED" | gcloud --configuration=horology-admin secrets versions add horology-graph-db --project=horology-dev --data-file=-'
```

3. Enable the Sheets and Drive APIs the job uses:

```bash
gcloud --configuration=horology-admin services enable sheets.googleapis.com drive.googleapis.com --project=horology-dev
```

4. Create the job's own identity and let it read the two graph secrets:

```bash
gcloud --configuration=horology-admin iam service-accounts create document-graph-sync --project=horology-dev --display-name="Document graph sheet sync"
```

```bash
for secret in horology-graph-db horology-graph-openrouter; do gcloud --configuration=horology-admin secrets add-iam-policy-binding "$secret" --project=horology-dev --member=serviceAccount:document-graph-sync@horology-dev.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor; done
```

5. **Approval.** In Google Drive, share with `document-graph-sync@horology-dev.iam.gserviceaccount.com`: the Document Index workbook as **Editor** (it writes Graph Sync Status, Graph Document ID and Last Synced Revision) and each folder holding indexed documents as **Viewer**. Do the same per workspace workbook later.

6. Build through [Cloud Build](cloud_build.md) and note the document-graph image digest. The same image serves the MCP and the job.

7. Create the job. Replace `DIGEST`; the workbook map is JSON, so the `^|^` prefix changes gcloud's list separator:

```bash
gcloud --configuration=horology run jobs create document-graph-sync --project=horology-dev --region=us-central1 --image=us-central1-docker.pkg.dev/horology-dev/mcp-servers/document-graph@sha256:DIGEST --command=python --args=-m,graph_sync --service-account=document-graph-sync@horology-dev.iam.gserviceaccount.com --set-secrets=DATABASE_URL_POOLED=horology-graph-db:2,OPENROUTER_API_KEY=horology-graph-openrouter:1 --set-env-vars='^|^GRAPH_SYNC_WORKBOOKS={"welladino":"1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc"}' --max-retries=0 --task-timeout=900s
```

8. Test the job by hand, then check the sheet's Graph Sync Status column and the execution log:

```bash
gcloud --configuration=horology run jobs execute document-graph-sync --project=horology-dev --region=us-central1 --wait
```

9. Let the document-graph service start that job, and only that job:

```bash
gcloud --configuration=horology-admin run jobs add-iam-policy-binding document-graph-sync --project=horology-dev --region=us-central1 --member=serviceAccount:document-graph@horology-dev.iam.gserviceaccount.com --role=roles/run.jobsExecutorWithOverrides
```

10. Sign-in credentials. Use the same Google OAuth client as the gateway, so one Audience test-user list covers both. In Google Auth Platform → Clients, add the redirect URI `https://document-graph-366292507424.us-central1.run.app/auth/google/callback`. Copy the client ID and secret into document-graph's own secrets (each identity reads only its own secrets), pasting each value when prompted:

```bash
gcloud --configuration=horology-admin secrets create horology-graph-google-client-id --project=horology-dev --replication-policy=automatic --data-file=-
```

```bash
gcloud --configuration=horology-admin secrets create horology-graph-google-client-secret --project=horology-dev --replication-policy=automatic --data-file=-
```

```bash
for secret in horology-graph-google-client-id horology-graph-google-client-secret; do gcloud --configuration=horology-admin secrets add-iam-policy-binding "$secret" --project=horology-dev --member=serviceAccount:document-graph@horology-dev.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor; done
```

11. Deploy the new image with sign-in on. Replace `DIGEST` and the email; each email maps to one workspace:

```bash
gcloud --configuration=horology run services update document-graph --project=horology-dev --region=us-central1 --image=us-central1-docker.pkg.dev/horology-dev/mcp-servers/document-graph@sha256:DIGEST --update-secrets=DATABASE_URL_POOLED=horology-graph-db:2,GOOGLE_OAUTH_CLIENT_ID=horology-graph-google-client-id:1,GOOGLE_OAUTH_CLIENT_SECRET=horology-graph-google-client-secret:1 --update-env-vars='^|^DOCUMENT_GRAPH_OAUTH_ENABLED=true|DOCUMENT_GRAPH_PUBLIC_URL=https://document-graph-366292507424.us-central1.run.app|DOCUMENT_GRAPH_WORKSPACES={"you@gmail.com":"welladino"}|GRAPH_SYNC_JOB=projects/horology-dev/locations/us-central1/jobs/document-graph-sync'
```

12. **Approval.** Sign-in now guards the service, so turn off Cloud Run's built-in invoker check (the same change made for the gateway on 2026-10-11):

```bash
gcloud --configuration=horology run services update document-graph --project=horology-dev --region=us-central1 --no-invoker-iam-check
```

13. Verify: anonymous `/mcp` returns 401; `/.well-known/oauth-authorization-server` returns 200; a test user connects from Claude (Customize → Connectors → add custom connector with `https://document-graph-366292507424.us-central1.run.app/mcp`) or Codex (`codex mcp add document-graph --url https://document-graph-366292507424.us-central1.run.app/mcp --oauth-client-registration dcr`); `list_documents` shows only that workspace; `sync_graph` starts an execution and the sheet updates.

Rollback: turn the invoker check back on first (`--invoker-iam-check`), then route traffic to `document-graph-00002-rks`. That old revision keeps its pinned `horology-graph-db:1` (owner login) and can still read, but its `write_document` fails because `workspace` is now required; treat it as read-only until the new revision is back.

To add a workspace later: copy the workbook, share it and its output folder with the job identity (step 5), add it to `GRAPH_SYNC_WORKBOOKS` on the job and its email to `DOCUMENT_GRAPH_WORKSPACES` on the service.

## Add or remove a person

Add: Google Auth Platform → Audience (`horology-dev`) → Test users → **Add users**. Keep publishing status **Testing**.

Remove:

1. Delete them from Audience test users, so they cannot sign in again.
2. Revoke their existing gateway tokens. From the repository root, with the gateway's private `GATEWAY_DATABASE_URL` from `mcp-servers/mcp-gateway/.env.local`:

```bash
set -a; . mcp-servers/mcp-gateway/.env.local; set +a; .venv/bin/python mcp-servers/mcp-gateway/scripts/revoke_email.py person@example.com
```

Their clients stop working within 15 minutes (access token lifetime). Only grants issued after the shared-access release carry an email; see the [note](../../planning/notes/2026-10-13_audience-signin-baked-policy_note.md).

## Routine deployment identity

Use `--configuration=horology` for builds and updates; it now selects the everyday account and impersonates `horology-deployer`. Use `--configuration=horology-admin` for IAM/infrastructure commands in earlier setup sections. See [IAM and deployment access](../architecture/gcp_access.md). Existing runtime accounts, secrets, ingress and live service revisions are unchanged by this IAM setup.

## 12 October read capability expansion

Gateway revision mcp-gateway-00008-kqw serves sha256:2fce0a9483aa16281a0c501c15bbe7f7ab19f698ed923bc809bab38e944ea46f with horology-gateway-policy:4, from successful Cloud Build 7d73cbd5-423c-4c29-bd45-64ac209228f5. Fixed Shopify/Alibaba/trends reads and Tavily basic extraction are deployed; owner advanced search is policy-enabled. Google, DataForSEO and the optional GitHub writer remain disabled. Assignment identities, expiry and recorded usage were preserved; existing exhausted paid allowances remain exhausted. See [expansion verification](../../planning/notes/2026-10-12_mcp-read-capabilities_note.md). Document graph's rebuilt candidate was not deployed.
