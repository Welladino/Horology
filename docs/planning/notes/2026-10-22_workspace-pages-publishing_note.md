# Private Pages publishing per workspace

## Topic

- workspace-pages-publishing

## Decision

Use the Horology Cloudflare account to host a separate Pages project for each workspace. A user supplies an approved email, not a Cloudflare credential or account membership. The MCP gateway derives the workspace from the verified Google email's sole active Neon membership. The one-email-one-workspace rule is an operating rule; the existing membership table still permits more than one, so publishing refuses zero or multiple memberships.

The workspace-to-project mapping lives in `access.workspace_pages`. An administrator creates or selects the Pages project, protects both `<project>.pages.dev` and `*.<project>.pages.dev` with separate Cloudflare Access applications, and registers the project and both application IDs using `scripts/ops/pages.py`. Registration leaves publishing disabled; the administrator explicitly enables it. Project names are unique across workspaces. A `pipeline-<ID>` branch supplies each item's stable URL.

Before uploading any HTML, the gateway reads the Pages project and both Access applications through centrally held API tokens. It requires exact expected hostnames and Allow policies containing only specific email addresses. The caller's email must be included, and all allowed emails must be active members of that workspace. Broad domain, Everyone, Bypass or unknown rules fail closed. Missing mapping, credentials, project, policy or user permission returns a `needs_admin_setup` result telling the agent to contact the Cloudflare administrator. API failures also prevent the upload. The service never accepts a project name, account ID, Access application ID or credential from an agent tool call.

Tavily and Firecrawl remain on their shared budgets. Pages publishing uses the existing zero-credit gateway reservation for usage accounting; it has no per-workspace spending limit. The gateway remains separate from Cloudflare Access administration: only an administrator can provision projects and policies. The code does not grant a workspace user Cloudflare dashboard access.

## Setup and release sequence

1. Apply migration `20261022_009`; it adds `access.workspace_pages` and read permission for the gateway login.
2. Provision a Pages project and two Access applications in the Horology Cloudflare account. Allow only the workspace's active member emails. Keep the main hostname and wildcard preview hostname protected.
3. Give the gateway a centrally held `CLOUDFLARE_PAGES_API_TOKEN` with Pages Read/Write and Access Apps/Policies Read. A separate `CLOUDFLARE_ACCESS_API_TOKEN` with Access read access is optional. Do not put tokens in policy JSON or source control.
4. Register the project and both app IDs with `scripts/ops/pages.py register`, then enable the mapping. A live Access check still runs before every upload.
5. Rebuild and deploy the gateway image. Existing Cloud Run revisions do not acquire this source automatically.

## Second-account check

Use a second personal Google account that belongs to a test workspace, not Welladino. Add it to the Google OAuth Audience test-user list and grant gateway access in Neon. First call `publish_synthesis` with no Pages mapping; expect `needs_admin_setup` and no deployment. Then configure and enable the test project's main and preview Access rules for that email and retry; expect only the test project's `pipeline-<ID>` URL. Verify both URLs redirect an unauthenticated visitor to Access, and verify the Welladino account cannot open the test artifact. Remove the test deployment and disable the mapping when the check is complete. Do not use private synthesis material for this test.

## Limits and follow-up

- The project and Access applications are administrator-provisioned; there is no automatic Cloudflare project creation on a tool call. This prevents an unprotected project from being populated before Access is ready.
- Access email membership is checked at publish time. If a person is removed from Horology later, an administrator must also remove them from Cloudflare Access; the gateway cannot revoke an already published page's viewer access.
- A successful Pages deployment does not prove the recipient can sign in; the second-account browser check is still required.
