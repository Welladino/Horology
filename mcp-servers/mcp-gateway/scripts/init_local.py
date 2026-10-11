"""Create ignored, mode-0600 local credentials and policy. Never print secrets."""
import hashlib
import json
from pathlib import Path
import secrets
import time

root = Path(__file__).resolve().parents[1]
(root / 'config').mkdir(exist_ok=True)
for filename in ('config/policy.local.json', '.env.local', 'config/client.local.json'):
    if (root / filename).exists():
        raise SystemExit(f'{filename} already exists; refusing to reset assignment budgets or credentials')
policy = json.loads((root / 'config/policy.example.json').read_text())
policy['assignments']['local-smoke']['expires_at'] = int(time.time()) + 86400
token = secrets.token_urlsafe(32)
hashes = json.dumps({hashlib.sha256(token.encode()).hexdigest(): 'local-smoke'}, separators=(',', ':'))
files = {
    'config/policy.local.json': json.dumps(policy, indent=2) + '\n',
    '.env.local': f"GATEWAY_TOKEN_HASHES='{hashes}'\nGITHUB_TOKEN=\nGOOGLE_READ_ACCESS_TOKEN=\nSUPABASE_METADATA_DSN=\nTAVILY_API_KEY=\nFIRECRAWL_API_KEY=\n",
    'config/client.local.json': json.dumps({'url': 'http://127.0.0.1:8767/mcp', 'headers': {'Authorization': 'Bearer ' + token}}, indent=2) + '\n',
}
for filename, content in files.items():
    path = root / filename
    with path.open('x') as output:
        path.chmod(0o600)
        output.write(content)
print('Created local policy, server environment and client credentials. No provider keys configured.')
