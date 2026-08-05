# Subagent Index

One line per subagent: name, one-line scope, file. Second-Soul reads this file to decide *which* persona is relevant, then reads that persona's own file in full before delegating — full persona text is never loaded until a delegation to that specific role is actually happening.

Adding a subagent = one line here + one new file in this folder. Never paste a persona's full content into this index or into `SOUL.md`.

| Name | Scope | File |
|---|---|---|
| GTM Manager | Positioning, channel/market strategy, sequencing, pricing-adjacent strategic questions | `/opt/data/personas/subagents/gtm-manager.md` |
| Marketing Executive | Copy, content drafts, campaign execution, messaging | `/opt/data/personas/subagents/marketing-executive.md` |
