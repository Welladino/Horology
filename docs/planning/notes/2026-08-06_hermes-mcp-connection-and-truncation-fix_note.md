# Implementation Note

## Topic
- hermes-mcp-connection-and-truncation-fix

## Context

Connected the document-graph MCP server (built in the prior note) to the running Hermes instance, and used it to retest the `delegate_task` output-truncation bug found earlier.

## Decision

**Connection mechanism: HTTP on the internal Docker network, not `docker exec` via a mounted socket.**

The natural way to connect Hermes to the MCP server would have been stdio transport via `docker exec -i horology-document-graph-mcp python server.py`, matching how `hermes mcp serve` itself works. That requires mounting `/var/run/docker.sock` into Hermes's own container — which grants that container control over *every* container on the host, not just this one. Rejected as too broad a permission grant for an autonomous agent container.

Switched `server.py` to `streamable-http` transport (`mcp.run(transport="streamable-http", host="0.0.0.0", port=8765)`) and removed the `sleep infinity` idle pattern from `docker-compose.yml` in favor of running the real server continuously. **No `ports:` mapping is published to the host** — the service is reachable only from other containers on the same Compose network, by service name (`http://document-graph-mcp:8765/mcp`). Verified both properties directly: a `curl` from the host to `localhost:8765` fails to connect; a `curl` from inside the `hermes` container to `http://document-graph-mcp:8765/mcp` succeeds (HTTP 400, which is the server correctly rejecting a bare GET without proper MCP session headers — confirms network reachability, not a failure).

Registered via:
```
printf "n\ny\n" | docker exec -i horology-hermes hermes mcp add document-graph --url http://document-graph-mcp:8765/mcp
```
(`hermes mcp add` prompts interactively for auth-required and enable-all-tools; piping `n`/`y` answers both non-interactively.)

**Delegation truncation-bug workaround: verified working, not just designed.**

Updated all three personas (`SOUL.md`, `gtm-manager.md`, `marketing-executive.md`) so subagents write their full answer via `write_document` before finishing, reporting back only a brief pointer (title/id) rather than relying on `delegate_task`'s return value — and so Second-Soul retrieves the real content via `get_document`/`list_documents` afterward rather than trusting whatever comes back from delegation directly.

Retested the exact GTM Manager delegation from the earlier truncation-bug note. Result: document `id=5` (`doc_type='recommendation'`, `created_by_agent='gtm-manager'`) was written with **7,875 characters of full content**, confirmed via direct DB query — not the ~100-character truncation seen before. Second-Soul correctly relayed the full recommendation to the founder by calling `get_document`, not by relaying `delegate_task`'s (still-broken) return value.

## Rationale

The Docker-socket-vs-HTTP decision follows the same principle as the earlier code-execution-vs-MCP decision: prefer the option with the narrowest possible blast radius, even when the broader option is faster to wire up. HTTP-on-internal-network with no published port gives Hermes exactly the one connection it needs and nothing else.

The truncation-bug workaround isn't a guess this time — it was retested against the same real business question used in the original bug report, and the result was checked directly against the database rather than trusted from the agent's own report of success (a lesson from this same session: an early attempt to verify the fix via a polling script produced a false positive due to a bug in the polling logic itself, caught only by cross-checking against Hermes's own session transcript and then the DB directly).

## Impact

- The document-graph MCP server is now a real, working part of the system, not just a standalone-verified component.
- The `delegate_task` truncation bug is no longer a blocker for real subagent work, as long as personas are written to route their output through `write_document` — this pattern should be applied to any future subagent persona by default, not treated as optional.
- `docs/runbook/mcp/document_graph_server.md` updated with the HTTP transport details and the `hermes mcp add` invocation.

## Follow-Ups

- Consider whether `list_documents`/`get_document` results should also flow into `link_documents` calls automatically when Second-Soul references one document while producing another (not yet tested).
- The upstream `delegate_task` truncation bug (NousResearch/hermes-agent#26425) and the cron-specific silent-drop variant (#70294) are unaffected by this workaround at the `delegate_task` protocol level — this note's fix works *around* the bug for output content specifically, but any other consequence of those bugs (e.g. #70294's cron behavior) has not been separately retested.
