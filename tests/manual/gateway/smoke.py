"""Local HTTP smoke test: real MCP handshake/auth; no provider credentials/calls."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

import httpx2 as httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run(url, token):
    async with httpx.AsyncClient() as client:
        for headers in ({}, {'Authorization': 'Bearer invalid'}):
            response = await client.post(url, headers=headers, json={})
            assert response.status_code == 401, response.status_code
    async with httpx.AsyncClient(headers={'Authorization': f'Bearer {token}'}) as transport_client, streamable_http_client(url, http_client=transport_client) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == {'tavily_search', 'tavily_extract_pages', 'gateway_status', 'supabase_performance_summary', 'firecrawl_alibaba_product', 'firecrawl_trends', 'firecrawl_scrape_page', 'firecrawl_shopify_search', 'firecrawl_alibaba_search', 'firecrawl_discover_tools', 'supabase_list_schema', 'supabase_describe_table', 'firecrawl_shopify_product', 'publish_synthesis'}
            assert 'github_create_planning_note' not in names
            removed = await session.call_tool('github_create_planning_note', {})
            assert removed.is_error
            status = await session.call_tool('gateway_status', {})
            assert not status.is_error
            denied = await session.call_tool('github_read_file', {'repository': 'other/repo', 'path': 'README.md', 'ref': 'main'})
            assert denied.is_error
            denied = await session.call_tool('drive_read_document', {'file_id': 'unknown'})
            assert denied.is_error
            print('PASS: MCP handshake, thirteen tools, authenticated status, invalid auth and scope denial; no provider calls')


def main():
    root = Path(__file__).resolve().parents[3] / 'mcp-servers/mcp-gateway'
    if '--existing' in sys.argv:
        client = json.loads((root.parents[1] / 'tests/manual/gateway/fixtures/private/client.local.json').read_text())
        asyncio.run(run(client['url'], client['headers']['Authorization'].removeprefix('Bearer ')))
        return
    token = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory() as tmp:
        policy = json.loads((root / 'config/policy.example.json').read_text())
        path = Path(tmp) / 'policy.json'
        path.write_text(json.dumps(policy))
        env = {k: v for k, v in os.environ.items() if k not in ('GITHUB_TOKEN', 'GOOGLE_READ_ACCESS_TOKEN', 'SUPABASE_METADATA_DSN', 'TAVILY_API_KEY', 'FIRECRAWL_API_KEY')}
        env.update(GATEWAY_POLICY=str(path), GATEWAY_BIND='127.0.0.1', GATEWAY_TOKEN_HASHES=json.dumps([hashlib.sha256(token.encode()).hexdigest()]))
        # Port deliberately fixed to the documented local port. Fail if occupied.
        import socket
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 8767))
        with open(Path(tmp) / 'server.log', 'w+') as log:
            process = subprocess.Popen([sys.executable, '-m', 'server'], cwd=root, env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    try:
                        httpx.get('http://127.0.0.1:8767/mcp', timeout=.2)
                        break
                    except httpx.ConnectError:
                        time.sleep(.05)
                asyncio.run(run('http://127.0.0.1:8767/mcp', token))
            finally:
                process.terminate()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
