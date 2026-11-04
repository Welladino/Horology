# Claude dispatch adapter

This adapter is packaged for the Claude supervisor. It handles only Pipeline Agent type **Claude Code**. The sheet value is authoritative: do not infer an Agent type, route Codex or ChatGPT Work rows, or run Manual or Unassigned rows.

Use **Claude Code** as `claim_item.agent_type` for every item this adapter dispatches.

Run from a checkout of the Horology repository so a cloud session clones the correct repository. Pass the item-mode prompt from `runs.md`.

## Claude desktop app: native sessions first

When the Claude desktop app's session tool (`start_session`) is available, use it instead of the CLI. It is the Claude equivalent of Codex's native desktop threads: each item gets a visible session the founder can open and steer.

1. Call `start_session` once per claimed item with the self-contained item-mode prompt, a short title containing the Pipeline ID, the Horology repository folder as `cwd` and its own worktree (`use_worktree: true`), cut from `main` unless the item names another base. For Cloud, pass `target: "cloud"`.
2. Record the returned session ID and pass it as `session_link` to `finish_run`.
3. Don't poll. The app notifies the supervisor when each session ends its turn; then check the session's branch, the sheets and its `finish_run` record before reporting. Use `SendMessage` to the session ID only for a founder-authorised follow-up, such as resuming a stopped run.
4. Start an item that builds on another item's unmerged work only after that work is merged, or from that item's branch.

## CLI fallback

Use the CLI when the session tool isn't available.

| Run location | Command |
|---|---|
| Local or blank | `claude -p "<prompt>" --permission-mode auto --output-format json` |
| Cloud | `claude --cloud "<prompt>"` |

- Start local sessions in the background, a few at a time, and record each session ID from its JSON output.
- `claude --cloud` returns a session link. Cloud sessions use the skills and connectors on the founder's claude.ai account, whatever repository they clone.
- Pass the session ID or link as `session_link` to `finish_run`. Where the harness can observe the session, wait for its result and report it; otherwise rely on the durable run record and saved outputs.
- If shell commands are unavailable (for example in claude.ai chat), run the selected items yourself in item mode, one at a time, using a subagent per item where the platform allows.
- If session creation fails, call `finish_run` as failed for a claimed item. Do not route it through another Agent type.
