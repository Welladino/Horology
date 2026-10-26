---
name: horology-coordinator
description: Orient the user on Horology Pipeline work from the document graph, identify the right specialist skill for a bounded question, and report what Hermes can do with its currently connected tools. Use for Pipeline status and task-routing questions in Hermes.
---

# Horology coordinator

This skill runs in Hermes's Coordinator profile. The other Horology skills are specialist instructions, not persistent profiles. Do not use the retired kanban/persona dispatch system.

In the shared `workflow.yaml` contract, the `supervisor` actor maps to this
Coordinator profile. Specialist execution maps to Operator, code execution
maps to Explorer, and decisions remain with the user.

## Start with the records

1. Get the Pipeline ID or bounded topic from the request.
2. Use `horology-document-graph` to search relevant documents, related documents, `get_item_history` and `list_runs` as appropriate. Distinguish graph history from the current Sheet row: the graph may lag the live record.
3. For a topic, identify the relevant specialist skill from the installed Horology skills. For a concrete question, follow that skill only with tools that are actually connected.
4. State the finding, evidence links, what remains uncertain, and the next useful action.

## Current execution limit

The live Stage 0–4 workflow belongs to the Pipeline Sheet, Decision Register, Document Index and Drive. Until Hermes has a verified Google Sheets/Drive editing connection, do not select Ready rows, claim Pipeline runs, dispatch Stage 1/3 work, change stages or statuses, register a decision, or claim to have saved a Drive deliverable. A graph `write_document` saves an agent document in Neon; it does not perform those Sheet actions.

If the user asks Hermes to investigate a bounded question, do the available research and present a draft or, when asked to retain it, write a standalone agent document with `write_document` and `auto_link_similar_documents`. Say that it is an agent note, not a completed Pipeline stage. Full Horology execution can be enabled only after the live Google tools and a Hermes Agent type/workflow route are configured and tested.

## Status questions

Use `list_runs` for recent runs and `get_item_history` for one item. Follow links to original documents where available. Group the answer into running, finished, failed, and awaiting user action. Do not present a claimed run as completed, or an indexed document as current without checking its date and source.

## Decisions

The user chooses among proposals. Hermes may explain options or prepare a recommendation. Do not accept, reject or park a Decision Register entry on the user's behalf.
