"""Bounded HTTP transport for fixed provider operations."""
import json
import httpx
from horology_runtime.settings import TIMEOUTS
from policy import Denied

MAX_BYTES = 150_000

async def request(method, url, *, token, params=None, body=None):
    # Provider origins are literals at call sites. Redirects and environment proxies
    # are disabled so credentials cannot be forwarded to a different host.
    async with httpx.AsyncClient(timeout=TIMEOUTS.gateway_http, follow_redirects=False, trust_env=False) as client:
        async with client.stream(method, url, headers={'Authorization': f'Bearer {token}'}, params=params, json=body) as response:
            if response.status_code != 200:
                raise Denied(f'Provider rejected request (HTTP {response.status_code})')
            chunks, size = [], 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise Denied('Provider response exceeds safe size limit')
                chunks.append(chunk)
    return json.loads(b''.join(chunks))
