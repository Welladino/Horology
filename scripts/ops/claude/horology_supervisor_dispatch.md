# Claude dispatch adapter

This adapter is packaged for the Claude supervisor. It handles only Pipeline Agent type **Claude Code**. The sheet value is authoritative: do not infer an Agent type, route Codex or ChatGPT Work rows, or run Manual or Unassigned rows.

Use **Claude Code** as `claim_item.agent_type` for every item this adapter dispatches.

Run from a checkout of the Horology repository so a cloud session clones the correct repository. Pass the item-mode prompt from `runs.md`.

| Run location | Command |
|---|---|
| Local or blank | `claude -p "<prompt>" --permission-mode auto --output-format json` |
| Cloud | `claude --cloud "<prompt>"` |

- Start local sessions in the background, a few at a time, and record each session ID from its JSON output.
- `claude --cloud` returns a session link. Cloud sessions use the skills and connectors on the founder's claude.ai account, whatever repository they clone.
- Pass the session ID or link as `session_link` to `finish_run`. Where the harness can observe the session, wait for its result and report it; otherwise rely on the durable run record and saved outputs.
- If shell commands are unavailable (for example in claude.ai chat), run the selected items yourself in item mode, one at a time, using a subagent per item where the platform allows.
- If session creation fails, call `finish_run` as failed for a claimed item. Do not route it through another Agent type.
