"""The Pipeline workflow (workflow.yaml): allowed values, and whether a change is an expected move.

The file's home is the horology-workflows plugin; the document-graph image
carries a copy at /app/workflow.yaml. HOROLOGY_WORKFLOW overrides the path.
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

_REPO_COPY = (Path(__file__).resolve().parents[3] / "plugins" / "horology-workflows" / "skills"
              / "horology-capture-triage" / "references" / "workflow.yaml")
_IMAGE_COPY = Path("/app/workflow.yaml")


@lru_cache(maxsize=1)
def load():
    """The parsed workflow, or None when no copy is available (checks are then skipped)."""
    configured = os.environ.get("HOROLOGY_WORKFLOW", "").strip()
    for path in ([Path(configured)] if configured else [_IMAGE_COPY, _REPO_COPY]):
        if path.is_file():
            return yaml.safe_load(path.read_text())
    return None


def values(field):
    """Allowed values of a Pipeline field, or None if the workflow doesn't define it."""
    wf = load()
    spec = (wf or {}).get("fields", {}).get(field)
    return list(spec["values"]) if spec else None


def _as_list(value):
    return value if isinstance(value, list) else [value]


def expected(field, old, new):
    """True if some transition allows field to change from old to new, False if none does,
    None if the workflow doesn't govern this field (or isn't available).

    Checks one field at a time: it doesn't check the transition's other conditions (for example that
    Awaiting decision -> Handed off came from a Stage 3 review) or who made the change."""
    wf = load()
    if not wf or field not in wf.get("fields", {}):
        return None
    governed = False
    for transition in wf.get("transitions", []):
        if field not in transition["to"]:
            continue
        if not transition["from"]:  # creates an item (capture); never explains a change
            continue
        governed = True
        if new not in _as_list(transition["to"][field]):
            continue
        source = transition["from"].get(field)
        if source is None or old in _as_list(source):
            return True
    return False if governed else None
