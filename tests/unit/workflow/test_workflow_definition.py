"""The Pipeline workflow definition (workflow.yaml) is internally consistent and matches the Apps Scripts."""
import json
import re

import pytest
import yaml

from support.paths import CLICKUP_SYNC, DOCUMENT_GRAPH, PIPELINE_DECISIONS, WORKFLOW


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
            targets = set(_as_list(t["to"].get("Status", [])))
            if source & reached and targets - reached:
                reached |= targets
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
    # Completed sends a comment without changing the ClickUp task status.
    assert {s.lower() for s in wf["statuses"] if s != "Completed"} == keys
    assert "completed:true" in config


def test_pipeline_decisions_script_matches_the_decision_transitions(wf):
    rules = (PIPELINE_DECISIONS / "src" / "Rules.js").read_text()
    outcomes = json.loads("{" + re.search(r"OUTCOMES\s*=\s*\{(.*?)\};", rules, re.S).group(1) + "}")
    transitions = {t["id"]: t for t in wf["transitions"]}
    expected = {}
    for status, decision in wf["decisions"].items():
        for tid in decision.get("triggers", []):
            review = transitions[tid]["from"].get("Review stage")
            for stage in _as_list(review or wf["fields"]["Review stage"]["values"]):
                expected[f"{status}|{stage}"] = tid
    assert {k: v["transition"] for k, v in outcomes.items()} == expected
    for key, outcome in outcomes.items():
        to = transitions[outcome["transition"]]["to"]
        assert outcome["Status"] == to["Status"], key
        assert outcome["Agent status"] == to["Agent status"], key
        review_stage = key.split("|")[1]
        stage = ({"Investigation proposal": "Stage 1", "Specialist deliverable": "Stage 3",
                  "Implementation question": "Stage 3"}[review_stage]
                 if outcome["Stage"] == "REVIEW" else outcome["Stage"])
        assert stage in _as_list(to["Stage"]), key


def test_revise_matches_the_pipeline_decisions_script(wf):
    rules = (PIPELINE_DECISIONS / "src" / "Rules.js").read_text()
    script = json.loads(re.search(r"REVISE\s*=\s*(\{.*?\});", rules, re.S).group(1))
    revise = wf["revise"]
    transition = {t["id"]: t for t in wf["transitions"]}[revise["transition"]]
    assert script["transition"] == revise["transition"]
    assert script["decision_statuses"] == revise["decision_statuses"]
    assert script["item_statuses"] == revise["item_statuses"] == _as_list(transition["from"]["Status"])
    assert set(revise["decision_statuses"]) == {s for s, d in wf["decisions"].items() if d.get("triggers")}
    assert not {"Inbox", "Researching", "In progress", "Awaiting decision"} & set(revise["item_statuses"])
    # Every outcome a revision can apply is a move the revise transition allows.
    outcomes = json.loads("{" + re.search(r"OUTCOMES\s*=\s*\{(.*?)\};", rules, re.S).group(1) + "}")
    for key, outcome in outcomes.items():
        assert outcome["Status"] in _as_list(transition["to"]["Status"]), key
        assert outcome["Agent status"] in _as_list(transition["to"]["Agent status"]), key


def test_child_tabs_match_the_web_page(wf):
    tabs = wf["tabs"]
    assert tabs["Steps"]["workbook"] == "Pipeline" and tabs["Options"]["workbook"] == "Decision Register"
    for tab in tabs.values():
        assert set(tab["key"]) <= set(tab["columns"])
    web = (PIPELINE_DECISIONS / "src" / "WebApp.js").read_text()
    for name, tab in tabs.items():
        required = re.search(rf"readTab\(ids\.\w+, '{name}', \[(.*?)\]\)", web).group(1)
        assert set(re.findall(r"'([^']+)'", required)) <= set(tab["columns"]), name
        for column in tab["columns"]:
            assert f"'{column}'" in web or f".{column}" in web or f"['{column}']" in web, (name, column)


def test_register_ids_are_reserved_not_taken_from_the_sheet(wf):
    ids = wf["register_ids"]
    assert ids["decision"]["allocated_by"] == ids["document"]["allocated_by"] == "reserve_id"
    assert ids["find_rows_by"] == "ID"
    tools = (DOCUMENT_GRAPH / "document_graph" / "tools.py").read_text()
    assert "graph.reserve_id" in tools and "graph.check_register_write" in tools


def test_routes_split_the_types(wf):
    routes = wf["routes"]
    types = [t for r in routes.values() for t in r["types"]]
    assert sorted(types) == sorted(wf["fields"]["Type"]["values"]) and len(types) == len(set(types))
    assert "Stage 2" not in routes["implementation"]["stages"]
    for route in routes.values():
        assert set(route["stages"]) <= set(wf["stages"])


def test_each_route_starts_with_its_own_status(wf):
    transitions = {t["id"]: t for t in wf["transitions"]}
    routes = wf["routes"]
    assert transitions["start-run"]["from"]["Type"] == routes["investigation"]["types"]
    assert transitions["start-run"]["to"]["Status"] == "Researching"
    assert transitions["start-implementation"]["from"]["Type"] == routes["implementation"]["types"]
    assert transitions["start-implementation"]["to"]["Status"] == "In progress"


def test_implementation_route_skips_stage_2_and_resumes_at_stage_3(wf):
    transitions = {t["id"]: t for t in wf["transitions"]}
    assert transitions["plan-implementation"]["from"]["Stage"] == "Stage 1"
    assert transitions["plan-implementation"]["to"] == {"Stage": "Stage 3"}
    assert transitions["complete-implementation"]["to"]["Status"] == "Completed"
    assert transitions["complete-implementation"]["to"]["Stage"] == "Stage 3"
    question = transitions["raise-implementation-question"]["to"]
    assert question["Status"] == "Awaiting decision" and question["Review stage"] == "Implementation question"
    resume = transitions["resume-implementation"]
    assert resume["from"]["Review stage"] == "Implementation question"
    assert resume["to"] == {"Status": "In progress", "Stage": "Stage 3", "Agent status": "Ready"}
    for t in wf["transitions"]:
        if "In progress" in _as_list(t["from"].get("Status", [])) or t["to"].get("Status") == "In progress":
            assert "Stage 2" not in _as_list(t["to"].get("Stage", [])), t["id"]


def test_investigation_route_is_unchanged(wf):
    transitions = {t["id"]: t for t in wf["transitions"]}
    assert transitions["submit-for-review"]["to"] == {
        "Status": "Awaiting decision", "Stage": "Stage 2", "Review stage": "Investigation proposal",
        "Agent status": "No action"}
    assert transitions["synthesize-stage-3"]["to"] == {
        "Status": "Awaiting decision", "Stage": "Stage 4", "Review stage": "Specialist deliverable",
        "Agent status": "No action"}
    assert transitions["accept-stage-1"]["to"] == {"Status": "Approved", "Stage": "Stage 3", "Agent status": "Ready"}
    assert transitions["accept-stage-3"]["to"] == {"Status": "Completed", "Stage": "Stage 4", "Agent status": "No action"}


def test_type_list_matches_the_pipeline_decisions_script(wf):
    rules = (PIPELINE_DECISIONS / "src" / "ItemRules.js").read_text()
    types = re.search(r"'Type':\s*\[(.*?)\]", rules).group(1)
    assert re.findall(r"'([^']+)'", types) == wf["fields"]["Type"]["values"]
    implementation = re.search(r"IMPLEMENTATION_TYPES\s*=\s*\[(.*?)\]", rules).group(1)
    assert re.findall(r"'([^']+)'", implementation) == wf["routes"]["implementation"]["types"]
