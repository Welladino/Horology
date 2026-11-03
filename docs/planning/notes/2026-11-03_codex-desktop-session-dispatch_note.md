# Native Codex desktop session dispatch

## Topic
- codex-desktop-session-dispatch

## Context
- Codex supervisor dispatch previously documented `codex exec` and `codex cloud exec` as its primary session launch paths. Those child processes were not durable, visible desktop chats, so the dispatcher could not retain a thread ID or use the desktop's native completion and attention states.

## Decision
- Codex desktop dispatch now creates one visible native thread per claimed Pipeline item with `create_thread`, records its thread and host IDs, and coordinates the set with cursor-based `wait_threads` calls.
- The dispatcher sends the created thread ID to the item session once so its eventual `finish_run` record can retain that ID as `session_link`.
- `codex exec` and `codex cloud exec` remain explicit fallbacks only when native thread creation is unavailable before a thread exists. A created thread that fails or needs attention is reported rather than rerun through the CLI.
- Claude dispatch is unchanged.

## Rationale
- Native threads are visible in the Codex desktop sidebar, survive the dispatcher's immediate turn, and expose compact completion or attention state without polling whole conversations.
- Keeping CLI fallback narrow avoids duplicate runs after a native thread has already claimed work or changed repository and workspace state.

## Impact
- The supervisor skill and run reference now name the native desktop coordination tools and the exact fallback boundary.
- Standing workflow architecture and the operations runbook describe the durable thread ID and founder handoff for approvals or input.
- A workflow unit test prevents Codex dispatch from drifting back to CLI-first wording.

## Follow-Ups
- Rebuild and upload the `horology-workflows` Codex plugin release from version 0.6.9.
- No merge, plugin upload or deployment is part of Pipeline item 63.
