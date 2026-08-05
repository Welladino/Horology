# Implementation Note

## Topic
- delegation-output-truncation-bug

## Context

Ran the first real end-to-end delegation test: Second-Soul → GTM Manager, asking for a concrete first-channel GTM recommendation for the actual NLE business. Delegation mechanics worked correctly (right subagent chosen, full persona + business context correctly injected into `delegate_task`'s `context`, subagent reasoned and produced a real, substantive, on-target answer per the raw delegation log). But the answer that made it back to Second-Soul was truncated to roughly 100 characters (`"...+94 chars"` markers in the raw log), across three separate dispatch attempts.

Second-Soul behaved correctly given the bug: it did not fabricate a clean answer, explicitly told the founder the pipeline was truncating output across all three attempts, and reconstructed the likely full answer from watching the subagent's live transcript rather than presenting a guess as the real result — consistent with its persona's honesty instructions.

## Decision

Confirmed via web search this is a known, currently-open upstream bug in Hermes Agent, not specific to our setup:

- [Issue #26425](https://github.com/NousResearch/hermes-agent/issues/26425) — "Response truncated due to output length limit — still occurring after #7237 fix" (re-opened after a prior fix attempt) — matches our symptom directly.
- [Issue #70294](https://github.com/NousResearch/hermes-agent/issues/70294) — cron jobs: top-level `delegate_task` results are silently dropped, yet the job reports `ok`. More concerning than the interactive-chat truncation: this means a scheduled/cron delegation could fail silently with no error surfaced at all, unlike the interactive case where Second-Soul at least knew something was wrong.

**Decision: do not treat `delegate_task`'s returned summary as reliable for getting full subagent output back to Second-Soul, especially under cron.** Options to consider before relying on delegation for real work:

1. **Workaround: have subagents write full output to a file instead of returning it inline.** Since subagents have file-tool access, instruct the persona (or the delegation `context`) to write its full answer to a file under `/opt/data/...`, then have Second-Soul read that file directly rather than relying on `delegate_task`'s own return value. Not yet tested.
2. **Wait for upstream fix** — both issues are open; worth checking status before investing heavily in a workaround, since a real fix would be a cleaner long-term answer than a file-based bypass.
3. **Reduce reliance on delegation for anything where a truncated/silently-dropped answer would be costly** — until (1) or (2) is confirmed reliable, treat delegated subagent output as needing verification (e.g. don't trust a cron-triggered delegation's result without checking logs), especially given #70294's silent-failure risk under the exact scheduled-run pattern Horology is built around.

Not yet decided which of these to pursue — flagging as the immediate next investigation before building more on top of delegation.

## Rationale

The bug is real, documented upstream, and directly affects the exact two things Horology's design depends on most: getting real subagent output back to the supervisor, and doing so reliably under unattended cron execution. Better to surface and address this now, with two subagents and a test question, than discover it once cron jobs and more subagents are relying on the same broken path.

## Impact

- Delegation is confirmed *mechanically* correct (right subagent, right persona/context injection) but *not yet reliable* for getting results back — a meaningful caveat on everything built so far in `personas/`.
- Cron-based automation (the core of Horology's twice-daily supervisor design) is at higher risk than interactive use, per #70294's silent-failure behavior — worth treating this as a blocker to trust cron delegation before investigating further.

## Follow-Ups

- Test the file-based workaround (subagent writes full answer to a file, Second-Soul reads the file) before relying on delegation for anything real.
- Check current status of #26425 and #70294 upstream before committing further design around `delegate_task`.
- Do not schedule cron jobs that depend on `delegate_task` output until this is resolved or the file-based workaround is verified.
