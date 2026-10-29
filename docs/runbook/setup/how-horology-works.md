# How Horology works

Horology is a small team of AI agents that research, assess and plan work for you, while you keep the decisions. You keep a list of work in a Google Sheet, the agents do the work in Claude or Codex sessions, their results land as Google Docs in your Drive, and you accept, rework, park or reject each one. This page explains the pieces and how a piece of work moves through them. To set up your own, follow [Set up Horology](setup.md).

## The pieces

```mermaid
flowchart TB
  you["<b>You</b><br/>Choose the work, read the results, decide"]
  subgraph sheets["Your Google Sheets"]
    pipeline["<b>Pipeline</b><br/>The list of work items, with their status"]
    decisions["<b>Decision Register</b><br/>Your decisions and feedback"]
    index["<b>Document Index</b><br/>Every document the work produced"]
  end
  subgraph drive["Your Google Drive"]
    reference["<b>Agent reference folders</b><br/>Your own material, read for context"]
    output["<b>Agent output folders</b><br/>Where agents save their documents"]
    templates["<b>Templates</b><br/>Research, Direction, Plan and others"]
  end
  subgraph agents["Agents in Claude or Codex sessions"]
    supervisor["<b>Supervisor</b><br/>Picks the right specialist and checks the result"]
    specialists["<b>Specialists</b><br/>Research, technical assessment, security review,<br/>go-to-market, marketing, content"]
    helpers["<b>Planner, capture and digest</b><br/>Scope items, record ideas, report daily"]
    setup["<b>Workspace setup and templates</b><br/>Add domains and folders, write templates"]
  end
  watchers["<b>Watchers</b><br/>Scheduled agents that check something<br/>regularly and write a report"]
  dg[("<b>Document graph</b><br/>Searchable memory of what's been<br/>researched and decided")]
  scripts["<b>Apps Scripts</b><br/>Apply your decisions, add items by form,<br/>keep folders in step"]
  you --> pipeline
  you --> decisions
  pipeline -- "Ready work" --> supervisor
  supervisor --> specialists
  agents -- "read" --> reference
  agents -- "copy" --> templates
  agents -- "save" --> output
  agents -- "register" --> index
  agents -- "search before starting" --> dg
  index -- "documents you include" --> dg
  watchers -- "read" --> reference
  watchers -- "report" --> output
  scripts -- "move items on" --> pipeline
  decisions --> scripts

  classDef human fill:#e6f4ea,stroke:#137333,color:#137333
  classDef record fill:#e8f0fe,stroke:#1a73e8,color:#174ea6
  classDef file fill:#e0f2f1,stroke:#00796b,color:#00695c
  classDef agent fill:#f3e8fd,stroke:#9334e6,color:#681da8
  classDef automation fill:#fef7e0,stroke:#f9ab00,color:#7a4f01
  classDef memory fill:#f1f3f4,stroke:#5f6368,color:#202124
  class you human
  class pipeline,decisions,index record
  class reference,output,templates file
  class supervisor,specialists,helpers,setup,watchers agent
  class scripts automation
  class dg memory
```

| Piece                       | What it is                                                                                                                                                                                                                                                            | Who changes it                                                       |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Pipeline** (Google Sheet) | One row per piece of work: its question, domain, status, stage and which agent should take it. Its other tabs describe your workspace: **Locations** (your folders), **Domains** (built from Locations), **Templates** and **Registers** (links to the other sheets). | You and the agents                                                   |
| **Decision Register**       | One row per decision, with your feedback for rework                                                                                                                                                                                                                   | You, and agents propose                                              |
| **Document Index**          | One row per document the work produced, linked to its Pipeline item                                                                                                                                                                                                   | Agents                                                               |
| **Agent Register**          | Watchers tab: every scheduled agent (watchers, digest, planner, security review, graph sync) with its type, prompt and schedule; MCP tab: what the MCP tools allow                                                                                                    | You, with the watcher-setup skill                                    |
| **Drive folders**           | Grouped by domain (a business, product or area). Each folder in Locations has a type: **Hub** (a domain's root), **Node** (holds other folders), **Agent reference** (read for context), **Agent output** (agents save here), **Others** (not for agents)             | You create them; agents only save into Agent output folders          |
| **Skills**                  | The instructions each agent follows, installed in Claude and Codex                                                                                                                                                                                                    | Maintained in this repository                                        |
| **Document graph**          | A searchable store of past research and decisions, so agents build on what's known instead of starting over                                                                                                                                                           | Agents write to it; the sync job copies in documents you mark for it |
| **Apps Scripts**            | The Pipeline script serves the Horology workspace, applies decisions and checks Locations against Drive. An optional standalone script sends status and milestone comments to linked ClickUp tasks. | Web saves run on demand; optional ClickUp updates run hourly and after Pipeline edits |

## How a piece of work moves

```mermaid
flowchart TB
  capture["<b>Capture · Stage 0</b><br/>Add the idea or question.<br/>Nothing runs yet."]
  plan["<b>Scope · optional</b><br/>The planner sharpens the question<br/>or splits it into steps on the Steps tab."]
  ready["<b>Select · Stage 1</b><br/>Choose Claude or Codex<br/>and set Agent status Ready."]
  investigate["<b>Investigation run</b><br/>The supervisor claims the item,<br/>selects specialists and checks the work."]
  proposal["<b>Review · Stage 2</b><br/>Evidence, recommendation and<br/>a proposed decision are ready."]
  decision{"<b>Your decision</b><br/>What should happen next?"}
  deliverable["<b>Specialist deliverable · Stage 3</b><br/>The accepted proposal becomes<br/>the detailed piece of work."]
  synthesis["<b>Visual synthesis · Stage 4</b><br/>Created in the same run and<br/>returned with the deliverable."]
  revise["<b>Rework</b><br/>Your instructions return<br/>the item to Ready."]
  stopped["<b>Parked or rejected</b><br/>No agent action"]
  done["<b>Completed</b><br/>You accepted the specialist<br/>deliverable after Stage 4 review."]

  capture --> plan --> ready
  capture --> ready
  ready --> investigate --> proposal --> decision
  decision -->|Accept proposal| deliverable --> synthesis --> decision
  decision -->|Rework| revise --> ready
  decision -->|Park or reject| stopped
  decision -->|Accept specialist deliverable| done

  classDef captureStyle fill:#f1f3f4,stroke:#5f6368,color:#202124
  classDef selected fill:#e8f0fe,stroke:#1a73e8,color:#174ea6
  classDef agent fill:#f3e8fd,stroke:#9334e6,color:#681da8
  classDef review fill:#fef7e0,stroke:#f9ab00,color:#7a4f01
  classDef success fill:#e6f4ea,stroke:#137333,color:#137333
  classDef reviseStyle fill:#fce8e6,stroke:#c5221f,color:#a50e0e
  class capture,plan,stopped captureStyle
  class ready selected
  class investigate,deliverable,synthesis agent
  class proposal,decision review
  class done success
  class revise reviseStyle
```

Work uses five numbered stages, from capture at Stage 0 through synthesis at Stage 4:

| Stage                                | What happens                                                                                                                                                                   |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Stage 0, capture**                 | An idea or request is recorded. Nothing runs.                                                                                                                                  |
| **Stage 1, investigate and propose** | Agents research the question, or write a direction, plan or technical assessment, and propose what to do.                                                                      |
| **Stage 2, your decision**           | You review the documents and record a decision.                                                                                                                                |
| **Stage 3, the deliverable**         | For an accepted proposal, agents produce the detailed piece: a go-to-market plan, a marketing plan, content drafts, or a planning note for code. Then you review it once more. |
| **Stage 4, visual synthesis**        | In the same Stage 3 run, the supervisor creates a concise visual artifact that makes the deliverable easier to review. The deliverable and synthesis return together for your decision. |

Nothing runs by itself. A row marked Ready only says what should be done next; work starts when you ask a Claude Code or Codex session to "run the Ready items" or "run item 42". Agents never accept their own proposals, and approving research doesn't approve building anything.

## What the agents do

You talk to one agent, the **supervisor**, unless you name another. It reads the item, chooses the specialists, runs them, checks their work and reports back. Ask it "what's happening?" at any time.

| Agent                | Does                                                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Supervisor           | Runs Ready items, one session each; reports what ran and what it found                                                                            |
| Planner              | Turns a vague item (Agent status Plan) into a sharp question or steps on the Steps tab                                                                    |
| Capture and triage   | Records ideas and requests as Pipeline rows, without duplicates                                                                                   |
| Research             | Answers a bounded question with sources, options and a recommendation                                                                             |
| Technical assessment | Decides whether and how to build a software change: options, cost, effort, uncertainty                                                            |
| Security review      | Read-only review of a repository or system, with prioritised findings                                                                             |
| Go-to-market         | Who the customer is, positioning, first channels                                                                                                  |
| Marketing strategy   | A marketing plan once the go-to-market direction is agreed                                                                                        |
| Content planner      | A content calendar, briefs and draft copy                                                                                                         |
| Digest               | A daily Google Doc: counts, what finished, what's waiting on you, anything wrong                                                                  |
| Workspace setup      | Adds domains, businesses and folders: shows the folder tree, creates it after your yes, adds the Locations rows                                   |
| Template             | Writes or revises a document template, then offers to add it to the Templates tab                                                                 |
| Watcher setup        | Sets up a watcher, or schedules the digest, planner, a security review or the graph sync: its prompt, schedule and connectors, on Claude or Codex |

Before starting, agents search the document graph for what's already known, read your **Agent reference** folders for the item's domain, and copy the right template. They save only into **Agent output** folders and ask you when no folder fits; only the workspace-setup skill creates folders, after you approve them.

## Watchers

Some work isn't a one-off item but a standing question: what did competitors launch this week, what campaigns are they running, did prices change. A **watcher** answers one on a schedule.

Each watcher is a row on the **Watchers** tab of the Agent Register, with a self-contained prompt, plus a scheduled task that runs it: a Claude routine in Anthropic's cloud, or a Codex scheduled task. Each run reads its last report so it reports only what's new, reads the Agent reference folders its prompt names, searches with the connectors it's allowed, writes a dated report in an Agent output folder and adds it to the Document Index. It finds its previous report by its title in that folder. It never acts on what it finds; anything that needs action is flagged at the top of the report for you. Set one up, change it or pause it by asking: "watch what our competitors launch every week".

The same tab holds the other agents you can run on a schedule, each marked in its **Type** column: the **Digest** (daily report card), the **Planner** (scopes rows set to Plan), a periodic **Security review** of a repository, and the **Graph sync** (copies Document Index rows into the document graph). The supervisor is never scheduled: Pipeline work starts when you ask.

## Your part, day to day

1. **Add work** with **Horology workspace → Add Pipeline item**, by typing a row into Master, or by asking an agent to capture it.
2. **Mark what's next:** Plan for items that need scoping, Ready for items to run.
3. **Start a run:** "run the Ready items" in Claude Code or Codex.
4. **Read the results** in your Agent output folders, or ask the supervisor for a summary.
5. **Decide** in the Decision Register. Rework needs instructions; the item goes back to Ready with them.
6. **Keep your material current:** put the documents you want agents to use in Agent reference folders, and add new folders to Locations (then **Horology workspace → Folders → Check Drive & update Locations**).

The daily digest tells you what finished and what's waiting on you, so you don't need to check the sheets for that. Watcher reports land in their report folders on their own schedule.
