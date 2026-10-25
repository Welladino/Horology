# Hermes configuration

This folder contains the reviewed, Git-tracked configuration for the Operator and Explorer profiles. Their real `.env` files live beside the examples but are ignored by Git.

Live sessions, databases, logs, caches and generated gateway files stay in the Docker volume `horology-hermes-data`. The old ignored `hermes-data/` directory is retained as a rollback copy for now.

After intentionally changing a tracked profile file, copy it into the running container at the matching path below `/opt/data/profiles/`, set its owner to `501:20`, and restart Hermes.
