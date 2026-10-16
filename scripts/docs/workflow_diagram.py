"""Build the subscription-workflow diagram from workflow.yaml, then render it.

Usage: python3 scripts/docs/workflow_diagram.py

The layout is fixed here; every state and value shown comes from
plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml,
so the diagram changes when the workflow does. Writes
docs/architecture/diagrams/src/subscription_workflow.json and renders it.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml"
SPEC = ROOT / "docs/architecture/diagrams/src/subscription_workflow.json"


def outcome(transition):
    """Short text for what a transition sets, e.g. 'Approved · Stage 3 · Ready'."""
    parts = []
    for field in ("Status", "Stage", "Agent status", "Planner output"):
        value = transition["to"].get(field)
        if value is None:
            continue
        value = " or ".join(value) if isinstance(value, list) else value
        parts.append(f"{field} {value}" if field == "Planner output" else value)
    return " · ".join(parts)


def actors(transition):
    names = transition["actor"] if isinstance(transition["actor"], list) else [transition["actor"]]
    return " or ".join(names)


def card(t, icon, tone, title):
    return {"icon": icon, "tone": tone, "title": title, "text": f"{outcome(t)} (by {actors(t)})"}


def build(wf):
    t = {x["id"]: x for x in wf["transitions"]}
    stages = wf["stages"]
    agent = wf["fields"]["Agent status"]["values"]
    return {"rows": [
        {"step": f"Stage 0 · {stages['Stage 0']}", "text": f"{outcome(t['capture'])} (by {actors(t['capture'])})"},
        {"group": f"Selecting work · Agent status {' → '.join(agent)}", "tone": "grey", "rows": [{"cards": [
            card(t["request-plan"], "flow", "grey", "Ask for a plan"),
            card(t["planned"], "check", "purple", "Planner"),
            card(t["select"], "user", "blue", "Select for a run"),
        ]}]},
        {"group": f"Stage 1 · {stages['Stage 1']}", "tone": "blue", "rows": [{"cards": [
            card(t["start-run"], "cpu", "blue", "Run starts"),
            card(t["submit-for-review"], "sheet", "orange", "Submitted for review"),
            card(t["run-failed"], "loop", "grey", "Run failed"),
        ]}]},
        {"step": f"Stage 2 · {stages['Stage 2']}", "text": "The founder decides in the Decision Register; the sync applies it"},
        {"arrow": False, "cards": [
            card(t["accept-stage-1"], "check", "green", "Accept a Stage 1 proposal"),
            card(t["rework"], "loop", "orange", "Rework"),
            card(t["decide-park"], "box", "grey", "Park"),
            card(t["decide-reject"], "box", "grey", "Reject"),
        ]},
        {"step": f"Stage 3 · {stages['Stage 3']}", "text": "Runs again from Ready, then back to review"},
        {"cards": [card(t["accept-stage-3"], "check", "green", "Accept the deliverable")]},
    ]}


def main():
    wf = yaml.safe_load(WORKFLOW.read_text())
    SPEC.write_text(json.dumps(build(wf), indent=2, ensure_ascii=False) + "\n")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import render_diagrams
    render_diagrams.main([SPEC.stem])


if __name__ == "__main__":
    main()
