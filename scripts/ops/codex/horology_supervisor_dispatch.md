# Codex dispatch adapter

This adapter is packaged for the Codex desktop supervisor. It handles Pipeline Agent types **Codex** and **ChatGPT Work**. The sheet value is authoritative: do not infer an Agent type, route a Claude Code row or run Manual or Unassigned rows.

Use **Codex** as `claim_item.agent_type` for every item this adapter dispatches. That field records the claiming supervisor harness; the Pipeline row remains the source of truth for whether the child is Codex or ChatGPT Work.

## Resolve targets before claiming

- The supervisor may start without a selected project. For a Codex item, use the row's target fields (Link type, URL and GitHub branch) to identify its saved Codex project with `list_projects`; inspect project metadata only, not the repository contents. If there is no unambiguous saved project, report the item and do not claim it.
- ChatGPT Work is projectless and cloud-hosted. It is for non-code work that can use its connected apps and supplied context. A GitHub connection can expose committed repository content, but it does not provide the local checkout, uncommitted changes, local services or repository-only instructions.
- Do not ask a ChatGPT Work child to create a Codex child. The Codex supervisor creates every child session itself.

## Create sessions

Use the Codex desktop thread tools, not the Codex CLI.

| Agent type | Session target | Run location |
|---|---|---|
| Codex | The resolved saved project for Local, or its configured Codex cloud environment for Cloud | Follow the row; blank means Local |
| ChatGPT Work | `chatgptWorkCloud`, projectless | Always Cloud; use Cloud as the effective claim and report location without editing the row |

1. Call `create_thread` once per claimed item with the self-contained item-mode prompt and a short title containing the Pipeline ID. Do not create a worktree unless the item or founder explicitly asks for one.
2. Record the returned thread or client-thread ID. Resolve a pending client-thread ID through `list_threads` before using thread coordination tools.
3. Once the real thread exists, send one coordination follow-up with `send_message_to_thread`: give it the thread ID and tell it to pass that value as `session_link` to `finish_run`. Do not send repeated progress prompts.
4. If creation fails, call `finish_run` as failed for a claimed item. Do not fall back to a CLI or a different Agent type.

## Monitor and report

- For Codex threads, use bounded `wait_threads` calls and retain each cursor as `afterCursor`. Leave approval and user-input requests in the item thread for the founder. Use `read_thread` only when the compact wait result does not identify the action needed.
- `wait_threads` does not monitor ChatGPT Work. Resolve its thread with `list_threads`, then use bounded `read_thread` checks with backoff until it completes or needs attention. Avoid tight polling.
- `send_message_to_thread` may send a founder-authorised correction or follow-up to either kind of child. Never answer an approval or founder decision on the founder's behalf.
- A child may use its own subagents. The child consolidates their work, checks it and returns one result; this supervisor reports that result and relies on the saved outputs and `finish_run` record for durable status.
