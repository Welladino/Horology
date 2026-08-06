# Research Brief

## Topic
- mcp-transport-isolation

## Question
- How should Hermes connect to the document-graph MCP server: the natural approach (stdio via `docker exec`, matching how `hermes mcp serve` itself works) requires mounting `/var/run/docker.sock` into Hermes's own container. Is that an acceptable permission grant, or is there a narrower alternative?

## Summary
- Mounting the Docker socket into Hermes's container would give it control over every container on the host, not just the one MCP server it needs to reach — too broad a grant for an autonomous agent container.
- `streamable-http` transport with no published host port gives the same practical isolation (Hermes can reach only this one service) without the Docker-socket escalation.

## Sources
- `mcp` Python SDK's `MCPServer.run()` transport options (`stdio`, `sse`, `streamable-http`).
- Direct verification: `curl` from host vs. from inside the `hermes` container against the MCP server's port.

## Findings
- stdio-via-`docker exec` is how `hermes mcp serve` itself works, and was the original plan — but it requires the *calling* side to have Docker control over the *target* container, which in Hermes's case means mounting the host's Docker socket into Hermes's own container.
- A container with the Docker socket mounted can start/stop/inspect any container on the host, not just the intended target — a significant, unscoped escalation for an autonomous agent.
- `streamable-http` transport with no `ports:` mapping in `docker-compose.yml` achieves the same effective isolation: reachable only from sibling containers on the same Compose network, by service name, with nothing published to the host at all.
- Verified directly: `curl http://localhost:<port>` from the host fails to connect; `curl http://<service-name>:<port>` from inside the Hermes container succeeds (with a 400 for a bare GET without proper MCP session headers, confirming network reachability rather than failure).

## Recommendation
- Use `streamable-http` transport, no host port published, for any future MCP server this project builds — this is now the established pattern (also used for the GitHub monitoring MCP server built later).
- Do not mount the Docker socket into any agent-controlled container for this project.

## Open Questions
- None outstanding — this was resolved and adopted as the standing pattern.
