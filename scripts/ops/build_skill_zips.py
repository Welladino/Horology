"""Build one zip per skill under plugins/*/skills/, for uploading to claude.ai.

claude.ai keeps each skill on its own, so a link into another skill's folder
(../horology-research/references/linking.md) would break. Those files are
copied into this skill's references/ and the links rewritten; files they link
to beside them come too. OpenAI-only agents/ folders are left out. From the
repository root:

    python3 scripts/ops/build_skill_zips.py                   # all skills
    python3 scripts/ops/build_skill_zips.py horology-planner  # just these

Zips land in plugins/dist/skills/ (git-ignored). Upload each changed one on
claude.ai: docs/runbook/subscription-agents/claude_skills.md.
"""
import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'plugins' / 'dist' / 'skills'
CROSS = re.compile(r'\]\(\.\./([\w-]+)/references/([^)#\s]+)\)')
SIBLING = re.compile(r'\]\(([\w.-]+\.(?:md|yaml))\)')


def build(name, src, skills):
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / name
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('agents', '.DS_Store', '__pycache__'))
        pulled = []
        for md in list(dst.rglob('*.md')):
            text = md.read_text()
            for other, file in set(CROSS.findall(text)):
                queue = [file]
                while queue:
                    f = queue.pop()
                    target = dst / 'references' / f
                    if target.exists():
                        continue
                    origin = skills[other] / 'references' / f
                    target.parent.mkdir(exist_ok=True)
                    shutil.copy2(origin, target)
                    pulled.append(f'{other}/{f}')
                    if origin.suffix == '.md':
                        queue += SIBLING.findall(origin.read_text())
            prefix = 'references/' if md.parent == dst else ''
            md.write_text(CROSS.sub(lambda m: f']({prefix}{m.group(2)})', text))
        broken = [str(p.relative_to(dst)) for p in dst.rglob('*.md') if '](../' in p.read_text()]
        if broken:
            sys.exit(f'{name}: links outside the skill remain in {", ".join(broken)}')
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f'{name}.zip').unlink(missing_ok=True)
        shutil.make_archive(str(OUT / name), 'zip', tmp, name)
        print(f'{name}.zip' + (f'  + {", ".join(pulled)}' if pulled else ''))


def main():
    parser = argparse.ArgumentParser(description='Build claude.ai skill zips.')
    parser.add_argument('names', nargs='*', help='skills to build (default: all)')
    args = parser.parse_args()
    skills = {p.parent.name: p.parent for p in REPO.glob('plugins/*/skills/*/SKILL.md')}
    unknown = set(args.names) - set(skills)
    if unknown:
        sys.exit(f'Unknown skills: {", ".join(sorted(unknown))}')
    for name in sorted(args.names or skills):
        build(name, skills[name], skills)
    print(f'Zips in {OUT.relative_to(REPO)}/')


if __name__ == '__main__':
    main()
