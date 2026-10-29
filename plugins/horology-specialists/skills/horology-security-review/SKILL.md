---
name: horology-security-review
description: Read-only security review of a repository or system named in a Pipeline item — dependency alerts, secrets, authentication and access, configuration, CI and infrastructure settings — with prioritised findings and suggested fixes. Produces an analysis for the founder; never changes code or settings. Usually run by horology-supervisor; use directly only when this skill is named.
---

# Security review

## When to use

A Pipeline item asking whether something is secure, what the security risks are, or what a dependency or configuration alert means for the codebase. Also for a periodic security check of a named repository. Not for feasibility or design of a change (use `horology-technical-assessment`), and never for fixing issues.

## Required context and locations

- Read [domains, folders and templates](../horology-research/references/locations.md) before choosing a domain or entity, reading context or saving anything.
- Follow the [presentation rules](../horology-research/references/presentation.md) when creating or filling documents.
- Read [linking rules](../horology-research/references/linking.md) when saving outputs.
- Resolve the permanent Pipeline ID and the scope. Read Link type, URL and GitHub branch; verify the repository remote, branch and the commit you inspect before making claims. Use read-only access only. If no repository access is available, report it and stop.
- Search the document graph for earlier security reviews of the same target so you report what changed, not the same list again.

## Workflow

1. Read the repository's own instructions and any security or architecture docs first.
2. Check, as far as the scope and access allow:
   - dependency alerts and known-vulnerable versions, and whether the affected code paths are actually used;
   - committed secrets, credentials in config or logs, and how secrets are loaded;
   - authentication, authorisation and session handling;
   - input handling at trust boundaries (user input, URLs, files, SQL, shell);
   - CI and deployment settings: who can deploy, what gates run, what runs with which permissions;
   - infrastructure exposure: public endpoints, ports, IAM roles, logging of sensitive data.
3. For each finding record: severity (Critical, High, Medium, Low), evidence (file and line, commit, alert ID or setting), whether it is exploitable in this codebase's actual use, and a suggested fix with rough effort.
4. Separate verified findings from suspicions you couldn't confirm. A clean area gets one line, not padding.
5. Compare with the last review: what's new, what's fixed, what's unchanged.
6. Save the analysis from the Technical Assessment or closest template in the Templates tab, in the Agent output folder for technical research, and register it in the Document Index with a reserved Document ID, following the register ID and ownership rules in the linking rules. Set the Pipeline item to Awaiting decision when ready.

## Decision and permission boundaries

- Read-only: no commits, pull requests, issues, comments, setting changes or secret rotation.
- Don't run exploit attempts against live systems or probe internal or metadata addresses.
- Don't copy secret values into documents, tickets or chat; name where they are instead.
- Report alert lists as samples when the tool returns a bounded number; never as the total.
- The founder decides what to fix and when.

## Output requirements

- A security analysis: scope and inspected revision, prioritised findings with evidence and suggested fixes, unverified suspicions, changes since the last review, and access gaps.
- A short report with the count of findings by severity and anything blocked.

## Verification before finishing

- Confirm every finding names its evidence and the revision it was found at.
- Confirm no secret values appear in the saved document.
- Read back the document and register rows; distinguish saved work from pending writes.
