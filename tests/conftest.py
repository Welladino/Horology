"""Test kinds, by folder:

- unit/: no database, network or Docker; fakes and mocks only.
- integration/: a real, disposable migrated Postgres (skipped without the test URLs).
- system/: the real Docker Compose stack (skipped without Docker).
- manual/: helpers run by hand, not collected (smoke.py).
- support/: helpers shared across kinds.

This folder is on sys.path (pytest adds a root conftest's folder), so tests import `support`.
"""
collect_ignore = ["manual"]
