---
name: horology-workspace-setup
description: Add or change the workspace's domains, businesses (entities) and Drive folders, and keep the Pipeline's Locations, Templates and Registers tabs in step. Offers choices, shows the folder tree it will create, creates the folders only after the founder agrees, and adds their Locations rows. Use when the founder asks to add a domain or business, add or reorganise folders, mark folders for agents, or set up a new workspace.
---

# Workspace setup

## When to use

The founder wants to change where work lives: "add a domain for our new product", "add a business under this domain", "I need a research folder for X", "mark this folder for the agents", or setting up a workspace from scratch. Not for Pipeline items (use `horology-supervisor` or `horology-capture-triage`) or for writing a new template (use `horology-template`).

## Required context and locations

- Read [domains, folders and templates](../horology-capture-triage/references/locations.md): the Domains, Locations, Templates and Registers tabs, and what each Type means.
- The Pipeline workbook is the one this workspace uses ([Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit)). Read its Locations, Domains, Templates and Registers tabs by header name before proposing anything.
- Locations columns: Domain, Entity, Kind (Root folder, Entity folder, Subfolder), Parent (the parent folder's Name), Name, Type, Location (Drive folder link), Purpose. Type is one of:
  - **Hub:** a domain's root folder
  - **Node:** a folder that only holds other folders, including an entity folder
  - **Agent reference:** material agents read for context, never write to
  - **Agent output:** where agents save
  - **Others:** not for agents (registers, archives)
- A domain with entities goes Root folder → Entity folder → Subfolders. Names must be unique within a Domain and Entity.
- Drive access with permission to create folders is required. If it isn't available, say so and stop before proposing folders.

## Ask with choices

Ask one question at a time. Offer a short numbered list of choices (or the platform's own choice prompt), with the likely answer first and "something else" last. Use what's already in the sheet to build the choices: existing domains, entities and folders.

Start with:

1. Add a domain
2. Add a business (entity) to a domain
3. Add folders to a domain or business
4. Change a folder's Type or Purpose
5. Add or update a Templates or Registers row (for a new template document, use `horology-template`)

## Workflow

1. Read the four tabs. For a new domain or entity, check it isn't a near-duplicate of an existing one (case, spelling, plural) and ask if it might be.
2. Work out the folders through choices:
   - **Where:** for a new domain, next to the existing domains' root folders (the parent of an existing Hub folder in Drive), unless the founder names another place. For anything else, under the domain or entity folder it belongs to.
   - **Which folders:** offer the standard set first, then "pick from it" and "my own":
     - `01_Strategy` (Node) with `01_Direction` and `02_Plans` (Agent output)
     - `02_Research` (Node) with `01_Marketing`, `02_Tech` and `03_Product` (Agent output)
     - `03_Brand_and_Identity` (Agent reference)
   - **Numbering:** continue the parent folder's existing numbers, e.g. `04_` after `03_`.
   - **Type and Purpose** for each folder; offer a one-line Purpose the founder can accept or change.
3. **Show the plan before doing anything:** the folder tree, marking which folders exist and which are new, with each one's Type, then the Locations rows to be added. For example:

   ```
   04_Shop                     Hub        new
   └─ 01_Caps                  Node       new   (entity: Caps)
      ├─ 01_Strategy           Agent output   new
      └─ 02_Brand              Agent reference new
   ```

   Ask: create it as shown, change something, or cancel.
4. **After a clear yes**, create only the new folders shown, parents first, and note each folder's link.
5. Add the Locations rows: parents before children, after the domain's existing rows. Fill every column; Location is the new folder's link. Change other rows only when the founder asked for that change and confirmed it.
6. For Templates or Registers changes, show the row first, then write it after a yes.
7. Read back what you wrote: no duplicate Domain, Entity and Name; every Parent exists; the Domains tab now lists the new domain or entity. The Domains tab is a formula; never write to it.

## Decision and permission boundaries

- This is the only skill that creates folders, and only the folders in a tree the founder has just approved. Never move, rename, delete or share Drive folders or files.
- To rename a folder or domain, ask the founder to rename it in Drive, then run **Extensions → Horology — Workbook → Check folders against Drive**, which updates Name and Parent. A domain or entity renamed in Locations also needs the same change on its existing Pipeline Master, Decision Register and Document Index rows: list those rows and offer to update them, and change them only after a yes. If ClickUp Sync mirrors the domain, its `LIST_<Domain>` Script Property needs the new name too; the founder changes that in the ClickUp Sync project.
- Don't create Pipeline items or change their status.

## Output requirements

- The tree as created, with links, and the rows added to Locations, Templates or Registers.
- Reminders, as they apply:
  - run **Extensions → Horology — Workbook → Check folders against Drive** to confirm the rows match Drive
  - update the Domain name on existing rows, and in ClickUp Sync, after a rename
  - put the material agents should read into the new Agent reference folders

## Verification before finishing

- Every new folder exists in Drive under the parent shown in the plan, and its Locations row links to it.
- The Locations checks show no red (duplicate) or orange (broken structure) rows for what you added.
- Distinguish what was created and written from anything still pending.
