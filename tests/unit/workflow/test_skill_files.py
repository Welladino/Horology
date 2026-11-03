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


# HOR-6: "next unused ID" from the sheet let parallel runs overwrite each other's register rows.
STALE_ALLOCATION = [r"next (unused|free) (numeric )?(document |decision )?id", r"max ?\+ ?1 from",
                    r"concurrent allocation is not implemented", r"coordinated allocator is required"]


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: str(p.relative_to(PLUGINS)))
def test_register_ids_are_never_taken_from_the_sheet(path):
    text = path.read_text().lower()
    allowed = "pipeline id" if "capture-triage" in str(path) else None  # Pipeline IDs: the form allocates them
    for pattern in STALE_ALLOCATION:
        for match in re.finditer(pattern, text):
            line = text[text.rfind("\n", 0, match.start()) + 1:text.find("\n", match.end())]
            assert allowed and allowed in line, f"{path.name}: '{match.group(0)}' - use reserve_id"


def test_codex_dispatch_prefers_native_desktop_threads():
    supervisor = (PLUGINS / "horology-workflows/skills/horology-supervisor/SKILL.md").read_text()
    runs = (PLUGINS / "horology-workflows/skills/horology-supervisor/references/runs.md").read_text()

    assert "`create_thread`" in supervisor
    assert "`wait_threads`" in supervisor
    assert "native thread ID" in supervisor
    assert runs.index("`create_thread`") < runs.index('`codex exec "<prompt>"`')
    assert "explicit fallback, not the default" in runs
    assert "before creating a thread" in runs
    assert "`send_message_to_thread`" in runs
    assert "pass it as `session_link` to `finish_run`" in runs
