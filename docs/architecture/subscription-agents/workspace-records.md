# Workspace records

Horology uses four Google Sheets workbooks as its human-readable operating record. They are intentionally ordinary Sheets: a non-developer can inspect and correct them, filters work normally, and a workspace can be copied without deploying a new application.

The workbook links are private workspace configuration. Public documentation describes their shape but does not point to a person's live copies.

## Pipeline workbook

The Pipeline is the main control surface. Work is selected here, but a row never starts an agent by itself.

| Tab | Purpose |
| --- | --- |
| **Master** | One row per work item. It holds the permanent Pipeline ID, title, domain and optional entity, lifecycle status and stage, review state, agent platform, next question or numbered steps, linked repository or external task, and document/decision references. |
| **Locations** | The workspace's Drive folder directory. This is the source of truth for where agents read and write; the repository does not prescribe folder names or a fixed tree. |
| **Domains** | A derived view of the root folders and entity folders in Locations. Agents use it as the valid list of domains and entities. Add or change the corresponding Locations row instead of editing this tab directly. |
| **Templates** | Links to document templates and a short description of when each is appropriate. Agents copy templates; they do not modify the originals. |
| **Registers** | Links to the Pipeline and the other three workbooks, with a short statement of each register's role. |
| **Read Me** | Field definitions and operating rules for the workbook. |
| **_ClickUp Sync** | Internal state for the optional ClickUp integration. It is not the everyday editing surface. |

### Locations controls Drive

Users may choose their own Drive layout. Each folder occupies one Locations row:

| Field | Meaning |
| --- | --- |
| Domain | Any stable name for a business, product or area of work |
| Entity | An optional named business within a domain |
| Kind | Root folder, Entity folder or Subfolder |
| Parent | The parent folder's Name within the same domain/entity; blank for a root |
| Name | The visible Drive folder name |
| Type | Hub, Node, Agent reference, Agent output or Others |
| Location | The actual Drive folder URL that agents use |
| Purpose | Optional guidance about what belongs there |

**Agent reference** folders contain source material an agent may read. **Agent output** folders are approved destinations for deliverables. **Hub** and **Node** define structure, while **Others** is outside agent work. Agents use the Location URL rather than guessing from a folder name. Only the workspace-setup skill creates folders, and it asks for approval before doing so.

This means examples such as Strategy, Research or Brand are suggestions, not schema. A user can add different domains, entities and subfolders without changing code or rebuilding a skill.

## Decision Register

The Decision Register preserves the human review trail. Each row has its own permanent Decision ID and points back to a Pipeline ID. Agents get new Decision and Document IDs from the document graph's `reserve_id` and check ownership before every write; they never count up from the sheet, because parallel runs share these registers ([register IDs](../mcp/document-graph.md#register-ids)).

It records the question under review, the proposed or accepted choice, the reason, status, evidence links, rework instructions and any decision it supersedes. Agents may draft proposals; a human accepts, requests rework, parks or rejects them. A later review creates a new row instead of overwriting the earlier decision.

## Document Index

The Document Index is a catalog, not the file store. Drive remains the source file location; one index row records its permanent Document ID, title, Pipeline relationship, Drive URL, domain/entity, document type, approval state and optional predecessor.

The graph columns are explicit controls:

- **Graph Inclusion** chooses whether the document may enter searchable memory.
- **Graph Sync Status** reports pending, synced, not shared, too long or another error.
- **Graph Document ID** and **Last Synced Revision** show what was imported.

The workbook also contains controlled entity-type definitions and a reviewable list of extracted entities. Sync is on demand, so Drive and the Sheet may be newer than Neon's searchable copy.

## Agent Register

The Agent Register describes automation and access rather than ordinary work items.

- **Watchers** records scheduled agents: what to watch, reference and report locations, allowed connectors, schedule, platform, prompt and scheduler reference. A watcher reports; it does not act on its findings.
- **MCP** is the readable catalog of restricted tools: what each tool does, its boundary, prohibited behavior, cost/budget and sign-in requirements.

The register documents expected access, while service policy and code enforce the actual boundary.

## Which system is authoritative?

| Information | Authoritative place |
| --- | --- |
| Current work status and scope | Pipeline Master |
| Drive folder routing | Pipeline Locations |
| Human review and rework | Decision Register |
| Deliverable identity and graph eligibility | Document Index |
| Source material and finished files | Google Drive |
| Scheduled-agent specification | Agent Register |
| Agent run claims and outcomes | Neon run history |
| Searchable passages and derived graph | Neon document graph |
| Provider credentials | Secret Manager or private environment |

Apps Script supplies a lightweight interface over these records: add a Pipeline item, browse the folder tree, reconcile Drive names and parents, and apply decisions. It does not turn the Sheets into a multi-tenant application.
