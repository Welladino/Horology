# Hermes agent architecture

Hermes is the optional always-on agent runtime used alongside Horology. Its deployment is maintained in the private Watchmaker repository, not in this repository. Horology supplies the shared workflow, canonical skills and restricted MCP services; Watchmaker turns selected parts of that system into a persistent Operator and an isolated Explorer.

```mermaid
flowchart LR
  user["User"] --> operator["Operator<br/>trusted persistent work"]
  user --> explorer["Explorer<br/>isolated experiments"]
  operator --> skills["Adapted Horology skills"]
  operator --> graph["Document graph MCP"]
  operator --> gateway["Restricted gateway MCP"]
  operator --> workspace["Approved repositories<br/>Docker volume"]
  explorer --> modal["Ephemeral Modal sandbox"]
  graph --> neon[("Neon document history")]
  gateway --> providers["Permitted provider tools"]
  subscriptions["Claude, ChatGPT and Codex"] --> sheets["Pipeline, Sheets and Drive"]
  sheets --> sync["Graph sync"] --> neon
```

## Repository boundary

| Concern | Owner | Meaning |
| --- | --- | --- |
| Pipeline contract and canonical skills | Horology | Shared definitions used by subscription agents and adapted for Hermes |
| Apps Script, document graph and restricted gateway | Horology | Human-facing workflow plus controlled service access |
| Hermes image, Compose deployment and operations | Watchmaker | Versioned runtime configuration for the always-on agent |
| Operator and Explorer templates | Watchmaker | Reviewed identities, context, adapted skills and example configuration |
| Live Hermes sessions, credentials and machine settings | Watchmaker's ignored `runtime/hermes-data/` | Private state that must never enter Git |
| Approved repository checkouts | Docker volume `horology-hermes-workspace` | Persistent agent workspace with no host-repository bind mount |

The Watchmaker checkout existing on a Mac or VM does not give Hermes access to that machine's other folders. The container receives only two explicit mounts: its ignored runtime directory at `/opt/data` and the Docker-managed workspace volume at `/workspace`. It does not receive the Docker socket or a host home-directory mount.

## Operator and Explorer

**Operator** handles trusted, persistent work. It can read adapted Horology skills, connect to approved MCP servers, use its controlled Chromium browser and work on repositories explicitly cloned into `/workspace`. Browser sessions are headless and use a fresh, unauthenticated profile unless the user deliberately configures otherwise.

**Explorer** handles unfamiliar code and dependency experiments in ephemeral Modal sandboxes. Its sandbox does not inherit Operator's repository volume or credentials. The user selects Operator or Explorer when assigning work; automatic cross-profile delegation is not assumed.

## Service connections

Watchmaker and Horology's two local MCP projects join the external `horology_default` Docker network:

| Container | Host port | Container-to-container address |
| --- | ---: | --- |
| `horology-hermes` | 8642 API, 9119 dashboard | — |
| `horology-document-graph-mcp` | 8765 | `http://document-graph-mcp:8765/mcp` |
| `horology-mcp-gateway` | 8767 | `http://horology-mcp-gateway:8767/mcp` |

All published ports stay bound to `127.0.0.1`. The local document graph serves the configured workspace. The gateway uses a bearer credential and its own client policy. GitHub access is repository-scoped and separate from the Horology gateway. None of these connections automatically grants Google Sheets or Drive access.

## Skills and update responsibility

Horology remains the source for the cross-platform workflow and specialist skills under `plugins/`. Watchmaker keeps reviewed Hermes adaptations under `profiles/operator/skills/`; a sync script copies only those maintained files into the ignored live runtime. Updating a Horology plugin does not automatically overwrite an adapted Hermes skill because the two runtimes can have different tools and safety boundaries.

Hermes memory provides local continuity, not the shared system of record. Pipeline state and decisions belong in Sheets and Drive; searchable documents and run history belong in the document graph. Detailed setup, upgrades, profile synchronization, browser testing and recovery procedures live in Watchmaker's `README.md` and `docs/operations.md`.
