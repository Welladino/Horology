# Subscription agents naming

## Context and decision

Rename managed-agents/ to subscription-agents/ to make the cost model and scope
clear. Subscription agents use existing platform subscriptions for workflow work.
The ClickUp sync remains one component and runs on Google Apps Script.

The Drive overview is now Subscription agents — Framework Overview. Stable
Drive file IDs and .clasp.json target/rootDir remain unchanged. Existing historical
notes retain the former name as a record of the initial setup.

## Verification and boundaries

The sync runs selected rows sequentially under a script lock. It transfers
records and can mark Ready, but does not launch AI workers. This workflow has no
implemented concurrent agent dispatcher. Existing Hermes kanban/profile
infrastructure is a separate system, not a Pipeline runner.

No Apps Script upload or schedule change accompanies the rename.
