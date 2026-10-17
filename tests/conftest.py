"""Test kinds, by folder:

- unit/: no database, network or Docker; fakes and mocks only.
- integration/: a real, disposable migrated Postgres (skipped without the test URLs).
- system/: the real Docker Compose stack (skipped without Docker).
- manual/: helpers run by hand, not collected (smoke.py).
- support/: helpers shared across kinds.

This folder is on sys.path (pytest adds a root conftest's folder), so tests import `support`.
"""
collect_ignore = ["manual"]


import os  # noqa: E402

from support.paths import WORKFLOW  # noqa: E402

# graph_core finds workflow.yaml beside the repository only when installed
# editable; Cloud Build installs it as a package, so point it at the file.
os.environ.setdefault("HOROLOGY_WORKFLOW", str(WORKFLOW))
