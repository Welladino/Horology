# Implementation Note

## Topic

2026-10-11 — Move the shared MCP gateway and rename its Supabase role.

## Context

The founder chose `horology_agents` as the dedicated Supabase login role, deferred Google OAuth, and requested the gateway live alongside the existing MCP servers.

## Decision

Move `subscription-agents/mcp-gateway/` to `mcp-servers/mcp-gateway/`. Update startup commands and standing architecture links. Change the gateway credential check and documentation to require `horology_agents`; retain rejection of `postgres` and the previous role name.

## Rationale

The gateway is shared infrastructure. Keeping it under `mcp-servers/` avoids tying its deployment to the subscription-agent workflow. The role check must match the chosen dedicated database identity.

## Impact

Move existing ignored local credentials/policy with the gateway without printing or changing their values. Keep Docker project `mcp-gateway` and its persistent state volume so quota history survives the move. No database role changes, cloud deployment, Google OAuth implementation, or provider calls are performed. The Supabase DSN must use `horology_agents.pyywbjossvjngoxocdxk` for the pooler and that role’s password.

Verification: 39 tests passed; 14 unrelated main-stack Docker tests skipped. The rebuilt container passed real MCP initialization, 13-tool discovery, authentication and scope-denial checks. Docker inspection confirmed the relocated policy mount and existing `mcp-gateway_gateway-state` volume. No provider calls were made.

## Follow-Ups

Google OAuth remains deferred. Live Supabase role permissions, credentials and TLS still need verification. See [gateway setup](../../../mcp-servers/mcp-gateway/README.md).
