"""Create ignored, mode-0600 local credentials and policy. Never print secrets."""
import hashlib
import json
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
(root / 'config').mkdir(exist_ok=True)
client_path = root.parents[1] / 'tests/manual/gateway/fixtures/private/client.local.json'
client_path.parent.mkdir(parents=True, exist_ok=True)
if client_path.exists():
    raise SystemExit('Private local test client already exists; refusing to overwrite it')
for filename in ('config/policy.local.json', '.env.local'):
    if (root / filename).exists():
        raise SystemExit(f'{filename} already exists; refusing to overwrite existing settings or credentials')
policy = json.loads((root / 'config/policy.example.json').read_text())
token = secrets.token_urlsafe(32)
hashes = json.dumps([hashlib.sha256(token.encode()).hexdigest()], separators=(',', ':'))
files = {
    'config/policy.local.json': json.dumps(policy, indent=2) + '\n',
    '.env.local': f"GATEWAY_TOKEN_HASHES='{hashes}'\nGATEWAY_DATABASE_URL=\nSUPABASE_METADATA_DSN=\nTAVILY_API_KEY=\nFIRECRAWL_API_KEY=\n",
    client_path: json.dumps({'url': 'http://127.0.0.1:8767/mcp', 'headers': {'Authorization': 'Bearer ' + token}}, indent=2) + '\n',
}
for filename, content in files.items():
    path = filename if isinstance(filename, Path) else root / filename
    with path.open('x') as output:
        path.chmod(0o600)
        output.write(content)
print('Created local policy, server environment and client credentials. No provider keys configured.')
