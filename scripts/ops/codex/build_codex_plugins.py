"""Build Codex upload archives from .codex-plugin configuration and shared skills.

Run from any directory. Root package files exist only in plugins/dist/codex/.
"""
import argparse
import json
from pathlib import Path
import zipfile

REPO = Path(__file__).resolve().parents[3]


def build(source, output):
    config = source / '.codex-plugin'
    legacy = json.loads((config / 'plugin.json').read_text())
    extension = dict(legacy.get('extensions', {}).get('com.openai', {}))
    for key in ('interface', 'apps', 'hooks', 'requires_local_executor', 'publicationPolicy', 'id'):
        if key in legacy:
            extension[key] = legacy[key]
    manifest = {'$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'}
    for key in ('name', 'version', 'description', 'author', 'homepage', 'repository', 'license', 'keywords'):
        if key in legacy:
            manifest[key] = legacy[key]
    if (config / 'apps.json').exists():
        extension['apps'] = './.app.json'
    manifest['extensions'] = dict(legacy.get('extensions', {}))
    manifest['extensions']['com.openai'] = extension
    if len(extension['interface']['shortDescription']) > 30:
        raise ValueError('Plugin short description exceeds 30 characters')
    files = {'plugin.json': (json.dumps(manifest, indent=2) + '\n').encode()}
    # Fixed root paths are required in portable uploads, not in our source tree.
    for name in ('mcp.json', 'apps.json'):
        path = config / name
        if name == 'mcp.json' and (config / 'apps.json').exists():
            continue  # Registered cloud connection replaces bundled MCP wiring.
        if path.exists():
            json.loads(path.read_text())
            files['.app.json' if name == 'apps.json' else name] = path.read_bytes()
    for folder in ('skills', 'assets'):
        for path in sorted((source / folder).rglob('*')):
            if not path.is_file() or path.name == '.DS_Store' or '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                raise ValueError(f'Symlink is not a package file: {path}')
            files[path.relative_to(source).as_posix()] = path.read_bytes()
    expected = {p.parent.name for p in (source / 'skills').glob('*/SKILL.md')}
    actual = {Path(name).parent.name for name in files if name.startswith('skills/') and name.endswith('/SKILL.md')}
    if expected != actual:
        raise ValueError(f'Packaged skills differ: expected {expected}, got {actual}')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (source.name + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
        for name, data in sorted(files.items()):
            package.writestr(name, data)
    print(f'{source.name}: {len(actual)} skills -> {archive}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names', nargs='*')
    args = parser.parse_args()
    sources = {p.parent.parent.name: p.parent.parent for p in REPO.glob('plugins/*/.codex-plugin/plugin.json')}
    if set(args.names) - sources.keys():
        parser.error('Unknown plugin name')
    for name in sorted(args.names or sources):
        build(sources[name], REPO / 'plugins/dist/codex')


if __name__ == '__main__':
    main()
