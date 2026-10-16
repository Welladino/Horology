"""The Pipeline workflow definition (workflow.yaml) is internally consistent and matches the Apps Scripts."""
import json
import re

import pytest
import yaml

from support.paths import CLICKUP_SYNC, PIPELINE_DECISIONS, WORKFLOW


@pytest.fixture(scope="module")
def wf():
    return yaml.safe_load(WORKFLOW.read_text())


def _as_list(value):
    return value if isinstance(value, list) else [value]


def test_statuses_match_status_field(wf):
    assert set(wf["statuses"]) == set(wf["fields"]["Status"]["values"])


def test_status_stages_are_declared(wf):
    stages = set(wf["fields"]["Stage"]["values"])
    assert set(wf["stages"]) == stages
    for name, status in wf["statuses"].items():
        assert set(status["stages"]) <= stages, name


def test_transitions_use_declared_actors_fields_and_values(wf):
    actors, fields = set(wf["actors"]), wf["fields"]
    ids = [t["id"] for t in wf["transitions"]]
    assert len(ids) == len(set(ids)), "transition ids must be unique"
    for t in wf["transitions"]:
        assert set(_as_list(t["actor"])) <= actors, t["id"]
        assert t["when"].strip(), t["id"]
        for side in ("from", "to"):
            for field, value in t[side].items():
                assert field in fields, (t["id"], field)
                assert set(_as_list(value)) <= set(fields[field]["values"]), (t["id"], field, value)


def test_decisions_trigger_existing_transitions(wf):
    ids = {t["id"] for t in wf["transitions"]}
    for name, decision in wf["decisions"].items():
        assert set(decision.get("triggers", [])) <= ids, name


def test_every_status_is_reachable_from_capture(wf):
    reached = {"Inbox"}
    changed = True
    while changed:
        changed = False
        for t in wf["transitions"]:
            source = set(_as_list(t["from"].get("Status", list(reached))))
            target = t["to"].get("Status")
            if target and source & reached and target not in reached:
                reached.add(target)
                changed = True
    assert reached == set(wf["statuses"])


def test_run_transitions_use_declared_statuses(wf):
    statuses = set(wf["runs"]["statuses"])
    for t in wf["runs"]["transitions"]:
        assert {t["from"], t["to"]} <= statuses


def test_statuses_match_clickup_sync_status_map(wf):
    config = (CLICKUP_SYNC / "src" / "Config.js").read_text()
    block = re.search(r"STATUS_MAP\s*=\s*\{(.*?)\};", config, re.S).group(1)
    keys = {m.strip("'\" ") for m in re.findall(r"([\w' ]+):", block)}
    # The sync also accepts verb spellings (park, hand off, reject); every workflow status must be mapped.
    assert {s.lower() for s in wf["statuses"]} <= keys


def test_pipeline_decisions_script_matches_the_decision_transitions(wf):
    rules = (PIPELINE_DECISIONS / "src" / "Rules.js").read_text()
    outcomes = json.loads("{" + re.search(r"OUTCOMES\s*=\s*\{(.*?)\};", rules, re.S).group(1) + "}")
    transitions = {t["id"]: t for t in wf["transitions"]}
    expected = {}
    for status, decision in wf["decisions"].items():
        for tid in decision.get("triggers", []):
            review = transitions[tid]["from"].get("Review stage")
            for stage in _as_list(review or ["Stage 1", "Stage 3"]):
                expected[f"{status}|{stage}"] = tid
    assert {k: v["transition"] for k, v in outcomes.items()} == expected
    for key, outcome in outcomes.items():
        to = transitions[outcome["transition"]]["to"]
        assert outcome["Status"] == to["Status"], key
        assert outcome["Agent status"] == to["Agent status"], key
        stage = key.split("|")[1] if outcome["Stage"] == "REVIEW" else outcome["Stage"]
        assert stage in _as_list(to["Stage"]), key
