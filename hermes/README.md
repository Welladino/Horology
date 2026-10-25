# Hermes configuration

This folder contains the reviewed, Git-tracked configuration for the Coordinator, Operator and Explorer profiles. The live Coordinator is Hermes' protected `default` profile with a presentation-only display name. Real `.env` files live beside the examples but are ignored by Git.

- **Coordinator** — user-facing planning, approval, Kanban routing and synthesis.
- **Operator** — non-code research, browser, documents and connected-service work.
- **Explorer** — code execution and dependency experiments in ephemeral Modal sandboxes.

Live sessions, databases, logs, caches and generated gateway files stay in the Docker volume `horology-hermes-data`. The old ignored `hermes-data/` directory is retained as a rollback copy for now.

After intentionally changing a tracked profile file, copy it into the running container, set its owner to `501:20`, and restart Hermes. Coordinator maps to `/opt/data`; named profiles map below `/opt/data/profiles/`.
