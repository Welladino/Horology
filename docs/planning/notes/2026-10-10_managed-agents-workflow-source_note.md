# Managed agents workflow source

## Context

Welladino uses Sheets and Drive for proposals and decisions, subscription
agents for investigation/planning, and Apps Script for the ClickUp view.
Manual copying of modular scripts made change tracking difficult.

## Decision

Keep this infrastructure in Horology under managed-agents/, with clickup-sync/
as the first component. Maintain local source, test it and review changes before
publishing through clasp.

## Impact and verification

Clasp 3.1.0 is installed. After refreshing Google login, a read-only clone of the
existing Apps Script project succeeded on 10 October 2026. All 14 live files were
imported, including settings, list discovery, connection test and manifest.
Credentials remain outside Git. The local connection file is ignored.
Offline tests isolate deployment settings. No upload, trigger, remote execution,
Hermes, MCP or Docker change was performed.

## Follow-ups

Review and commit the imported baseline. Later publishing must include a source
review and live preview; existing triggers can use changed code after upload.
Subscription-agent scheduling and Neon backfill remain separate future work.
