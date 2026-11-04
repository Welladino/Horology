"""Skill files link only to shipped files and keep harness-specific dispatch separate."""
import importlib.util
import re
import zipfile

import pytest

from support.paths import PLUGINS, REPO

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


# HOR-9 / item 70: Pages links were stored nowhere the founder could see them.
def _publishing_skills():
    skills = {}
    for path in SKILL_FILES:
        skill = path.relative_to(PLUGINS).parts[:3]
        skills.setdefault(skill, []).append(path.read_text())
    return {"/".join(skill): "\n".join(texts) for skill, texts in skills.items() if "publish_synthesis" in "\n".join(texts)}


def test_a_skill_publishes_pages():
    assert "horology-specialists/skills/horology-synthesis-artifacts" in _publishing_skills()


@pytest.mark.parametrize("skill", sorted(_publishing_skills()))
def test_every_publishing_skill_lists_the_page_on_the_pages_tab(skill):
    text = _publishing_skills()[skill]
    assert "Pages** tab" in text or "Pages tab" in text, f"{skill} publishes but never adds a Pages tab row"
    assert "do not add a sheet column" not in text.lower()


IMPLEMENTATION_ROUTE_SKILLS = ["horology-supervisor", "horology-synthesis-artifacts"]


@pytest.mark.parametrize("skill", IMPLEMENTATION_ROUTE_SKILLS)
def test_implementation_route_ends_with_a_report_and_a_stage_4_page(skill):
    # Item 69 (04/11/2026): an Implementation report Doc at Stage 3, a page made from it at Stage 4.
    text = next(PLUGINS.glob(f"horology-*/skills/{skill}/SKILL.md")).read_text()
    assert "Implementation report" in text and "Stage 4" in text


def test_supervisor_writes_a_stage_1_document_and_leaves_graph_inclusion_alone():
    text = next(PLUGINS.glob("horology-*/skills/horology-supervisor/SKILL.md")).read_text()
    assert "complete-implementation" in text
    assert "Stage 1 document" in text
    assert "Graph Inclusion" in text and "never change it" in text


# Item 71 (04/11/2026): a Stage 4 page's HTML stays in Drive but gets no Document Index row or Document ID;
# the Pages tab lists the page, and its Document ID is the page's source document.
STAGE_4_HTML_INDEXED = [r"synthesis folder and its document index row", r"drive (html|artifact|copy) and (its )?document index",
                        r"and index rows are verified", r"the drive artifact's document id"]


@pytest.mark.parametrize("skill", sorted(_publishing_skills()) + ["horology-workflows/skills/horology-supervisor"])
def test_stage_4_html_gets_no_document_index_row(skill):
    text = "\n".join(p.read_text() for p in (PLUGINS / skill).rglob("*.md")).lower()
    for pattern in STAGE_4_HTML_INDEXED:
        assert not re.search(pattern, text), f"{skill}: '{pattern}' - Stage 4 HTML has no Document Index row"


def test_pages_tab_document_id_is_the_source_document():
    text = (PLUGINS / "horology-specialists/skills/horology-synthesis-artifacts/references/visuals-and-pages.md").read_text()
    row = next(line for line in text.splitlines() if line.startswith("| Document ID |"))
    assert "source document" in row and "Implementation report" in row


# Item 71 follow-up (04/11/2026): on the implementation route the Stage 4 page is made only on request,
# to save cost; the investigation route keeps its automatic Stage 4 synthesis.
def _skill_text(skill):
    return next(PLUGINS.glob(f"horology-*/skills/{skill}/SKILL.md")).read_text()


def test_implementation_route_makes_a_page_only_on_request():
    supervisor = _skill_text("horology-supervisor")
    route = supervisor[supervisor.index("## Implementation route"):supervisor.index("## Status mode")]
    assert "Don't invoke `horology-synthesis-artifacts`" in route
    assert "**Page on request.**" in route and "Pages tab" in route
    assert "Invoke `horology-synthesis-artifacts` in this same run" not in route
    synthesis = _skill_text("horology-synthesis-artifacts")
    assert "**Implementation route: on request only.**" in synthesis
    assert "The supervisor invokes this specialist as the final step of a Stage 3 run, on both routes" not in synthesis


def test_investigation_route_stage_4_synthesis_stays_automatic():
    supervisor = _skill_text("horology-supervisor")
    assert "For Stage 3, invoke `horology-synthesis-artifacts` in this same run" in supervisor
    assert "final step of every Stage 3 run" in _skill_text("horology-synthesis-artifacts")


def test_supervisor_core_delegates_dispatch_to_the_packaged_adapter():
    skill = PLUGINS / "horology-workflows/skills/horology-supervisor"
    supervisor = (skill / "SKILL.md").read_text()
    runs = (skill / "references/runs.md").read_text()
    codex = (skill / "references/dispatch.md").read_text()
    claude = (REPO / "scripts/ops/claude/horology_supervisor_dispatch.md").read_text()

    assert "[dispatch adapter](references/dispatch.md)" in supervisor
    assert "claiming supervisor harness" in runs
    assert "**Codex** and **ChatGPT Work**" in codex
    assert "Use **Codex** as `claim_item.agent_type`" in codex
    assert "`create_thread`" in codex and "`wait_threads`" in codex
    assert "Always Cloud" in codex
    assert "Codex CLI" in codex and "not the Codex CLI" in codex
    assert "only Pipeline Agent type **Claude Code**" in claude
    assert "`claude -p" in claude and "`claude --cloud" in claude
    assert "`start_session`" in claude and "CLI fallback" in claude
    assert "`create_thread`" not in claude


def test_claude_supervisor_zip_substitutes_only_its_dispatch_adapter(tmp_path):
    script = REPO / "scripts/ops/claude/build_skill_zips.py"
    spec = importlib.util.spec_from_file_location("build_skill_zips", script)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.OUT = tmp_path
    skills = {
        path.parent.name: path.parent
        for path in REPO.glob("plugins/*/skills/*/SKILL.md")
        if path.relative_to(REPO / "plugins").parts[0] not in builder.EXCLUDED_PLUGINS
    }

    builder.build("horology-supervisor", skills["horology-supervisor"], skills)

    with zipfile.ZipFile(tmp_path / "horology-supervisor.zip") as archive:
        dispatch = archive.read("horology-supervisor/references/dispatch.md").decode()
        supervisor = archive.read("horology-supervisor/SKILL.md").decode()
    assert "only Pipeline Agent type **Claude Code**" in dispatch
    assert "ChatGPT Work rows" in dispatch
    assert "`create_thread`" not in dispatch
    assert "[dispatch adapter](references/dispatch.md)" in supervisor
