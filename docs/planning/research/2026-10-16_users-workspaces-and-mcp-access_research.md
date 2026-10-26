# Research Brief

## Topic
- users-workspaces-and-mcp-access

## Question
- Workspaces and who may use which MCP server are JSON in Cloud Run settings (`DOCUMENT_GRAPH_WORKSPACES`, `GRAPH_SYNC_WORKBOOKS`), and the gateway allows any account Google lets sign in. Can users, workspaces and MCP access live in Neon instead, with a cache so each request stays cheap, and so new MCP servers are easy to add?

## Summary
- Yes: five tables in their own Neon schema `access` (`mcp_servers`, `workspaces`, `users`, `workspace_members`, `user_mcp_access`), read by every MCP server through one shared lookup cached for 5 minutes (LRU, size-capped).
- A person can belong to several workspaces; the workspace is chosen at sign-in (a picker on the consent page when there is more than one) and tied to that connection's tokens.
- MCP access is a link table (one row per person per server) rather than per-server columns or an array, so the database guarantees every grant names a real user and server, and a new server needs no schema change.

## Sources
- Current code: `mcp-servers/document-graph/document_graph/shared/workspace.py` (the email → workspace map), `shared-runtime/horology_runtime/oauth/provider.py` (the account check runs at sign-in, refresh and every token load), `mcp-servers/mcp-gateway/server.py` (its check only confirms the shared policy), `jobs/document-graph-sync/graph_sync/__main__.py` (`GRAPH_SYNC_WORKBOOKS`).
- Google Auth Platform: an app in Testing allows at most 100 test users; beyond that the app must be published and verified.
- [Execution history brief](2026-10-16_execution-history-in-neon_research.md): introduced the three-spreadsheet form of `GRAPH_SYNC_WORKBOOKS`.

## Findings
- **Today.** Adding, moving or removing a person means editing JSON on a Cloud Run service and redeploying; removal only takes effect after that. The gateway has no allow-list of its own: Google's Audience test users are the only gate.
- **Per-request cost.** The account check runs on every MCP request. A database lookup each time would add a round trip; a cache removes it.
- **LRU alone isn't enough.** An LRU keeps entries until space runs out, so a disabled user could stay allowed until a restart, separately on every Cloud Run instance. An expiry (TTL) bounds that: entries live 5 minutes (founder's choice), so any change applies everywhere within 5 minutes without a redeploy. A size cap (10,000 per instance) keeps memory flat however many users exist. Misses (unknown emails) are cached for 60 seconds, so a newly added person waits at most a minute.
- **Server access options.** One boolean column per server needs a migration per new server. An array of server IDs on `users` is compact, but the database can't check its values against `mcp_servers` (a typo is stored) and deleting a server leaves stale IDs. A link table `user_mcp_access (user_id, server_id)` with foreign keys rejects unknown servers and users, and can carry grant details. At scale it stays cheap: a million users with three servers each is three million short rows, and the check is one primary-key lookup, about the same as the array's lookup by email.
- **Several workspaces per person.** A request must know which workspace it is for. Options: pick at sign-in (token tied to one workspace), a separate address per workspace, or a `workspace` argument on every tool. Picking at sign-in changes no tools and can't be confused by an agent; the founder chose it. Tokens issued before this change carry no workspace: they keep working when the person has exactly one workspace, otherwise the connector must reconnect.
- **Keys.** Users get a permanent numeric `id`; email is a unique, lowercase lookup column, since people change addresses. Workspace names stay the text keys already stored in every scoped table (`documents.workspace`, `run_log.workspace` and so on); no foreign keys are added to those existing tables.
- **Who changes the tables.** The services only read them (SELECT for `horology_graph` and `horology_gateway`). An admin script using the owner connection, like migrations, adds and changes users, workspaces, members and grants, and can be run by the founder or an AI session.
- **Unchanged.** The Google Audience list still decides who may sign in at all, while the app stays in Testing. Local mode (Hermes Docker) keeps its single `DOCUMENT_GRAPH_WORKSPACE` and local bearer token.

## Recommendation
- Migration `20261016_008`, all in a new schema `access` (the only tables two services share, and the ones that decide who gets in; each service login gets USAGE on the schema and SELECT on its tables, and the gateway needs nothing in `public`):
  - `mcp_servers (id, display_name, active)`, seeded with `gateway` and `document-graph`; an inactive server is closed to everyone.
  - `workspaces (name, display_name, index_sheet_id, pipeline_sheet_id, decisions_sheet_id, active)`, replacing `GRAPH_SYNC_WORKBOOKS`.
  - `users (id, email, active, note, created_at)`.
  - `workspace_members (user_id, workspace, role owner|member)`.
  - `user_mcp_access (user_id, server_id, granted_at, note)`.
  - USAGE on `access` and SELECT on its tables for both service logins.
- `horology_runtime/access.py`: one lookup per email returns active status, active granted servers and active workspaces; cached 5 minutes, 10,000 entries, misses 60 seconds. `check(email, workspace)` raises unless the account is active, holds this server, and (for workspace-scoped servers) is a member of that workspace.
- The OAuth provider awaits the check, and asks a workspace-scoped service for the account's workspaces: none refuses sign-in, one is chosen silently, several show a picker. The chosen workspace is stored on the code, refresh and access tokens.
- The gateway checks `gateway`; the document graph checks `document-graph` and reads the workspace from the token; the sync job reads `workspaces` (`GRAPH_SYNC_WORKBOOKS` stays as a local override).
- `scripts/ops/mcp/access.py` for users, workspaces, members, grants and servers. After deploying, seed it from today's settings, then remove `DOCUMENT_GRAPH_WORKSPACES` and `GRAPH_SYNC_WORKBOOKS` from Cloud Run.

## Open Questions
- Instant revocation: a change takes up to 5 minutes (or a token's lifetime for tokens already cached). Should the admin script also revoke a disabled person's live tokens on both services? Today only the gateway has `revoke_email.py`.
- When the app leaves Testing (over 100 users), these tables become the only allow-list; sign-up and invitations would need designing then.
