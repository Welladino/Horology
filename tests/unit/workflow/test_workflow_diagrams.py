"""The workflow diagrams in the subscription-agents page match workflow.yaml."""
import re

import pytest
import yaml

from support.paths import REPO, WORKFLOW

PAGE = REPO / "docs" / "architecture" / "subscription-agents" / "workflow.md"


@pytest.fixture(scope="module")
def diagrams():
    return "\n".join(re.findall(r"```mermaid\n(.*?)```", PAGE.read_text(), re.S))


@pytest.fixture(scope="module")
def wf():
    return yaml.safe_load(WORKFLOW.read_text())


def test_every_move_is_drawn(wf, diagrams):
    missing = [t["id"] for t in wf["transitions"] if not re.search(rf"\b{re.escape(t['id'])}\b", diagrams)]
    assert not missing, f"moves in workflow.yaml missing from the diagrams: {missing}"


def test_every_status_and_agent_status_is_drawn(wf, diagrams):
    values = wf["fields"]["Status"]["values"] + wf["fields"]["Agent status"]["values"]
    assert not [v for v in values if v not in diagrams]
