"""Skill files link only to files their own plugin ships, shared copies stay identical, and no domain names are written in."""
import re

import pytest

from support.paths import PLUGINS

SKILL_FILES = sorted(p for p in PLUGINS.glob("horology-*/skills/**/*.md"))
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")

# References shared by both plugins. Codex packages each plugin on its own, so each keeps a copy.
SHARED = [
    ("horology-workflows/skills/horology-capture-triage/references/locations.md",
     "horology-specialists/skills/horology-research/references/locations.md"),
    ("horology-specialists/skills/horology-research/references/presentation.md",
     "horology-workflows/skills/horology-digest/references/presentation.md"),
]

# Domains and entities are read from the Pipeline's Domains tab, never written into skills.
DOMAIN_NAMES = ["Article Aggregator", "Newsletter", "Ecommerce", "Wovenpattern", "Cap brands"]


def _local_links(path):
    return [t for t in LINK.findall(path.read_text()) if not re.match(r"[a-z]+:", t)]


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: str(p.relative_to(PLUGINS)))
def test_links_resolve_inside_the_plugin(path):
    plugin = path.relative_to(PLUGINS).parts[0]
    for target in _local_links(path):
        resolved = (path.parent / target).resolve()
        assert resolved.exists(), f"{target} does not exist"
        assert resolved.is_relative_to((PLUGINS / plugin).resolve()), f"{target} leaves the {plugin} plugin"


@pytest.mark.parametrize("pair", SHARED, ids=lambda p: p[0].rsplit("/", 1)[-1])
def test_shared_copies_are_identical(pair):
    first, second = (PLUGINS / p for p in pair)
    assert first.read_text() == second.read_text()


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: str(p.relative_to(PLUGINS)))
def test_no_domain_names(path):
    text = path.read_text()
    assert not [name for name in DOMAIN_NAMES if name in text]
