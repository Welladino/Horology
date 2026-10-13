"""Start one sync job execution for one workspace; nothing else in Cloud Run is reachable."""
import asyncio
import os
import re

import httpx
from horology_runtime.settings import TIMEOUTS

JOB_NAME = re.compile(r"projects/[a-z0-9-]+/locations/[a-z0-9-]+/jobs/[a-z0-9-]+")
_credentials = None


async def _token():
    global _credentials
    if _credentials is None:
        import google.auth
        _credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not _credentials.valid:
        from google.auth.transport.requests import Request
        await asyncio.to_thread(_credentials.refresh, Request())
    return _credentials.token


async def start_sync(workspace):
    job = os.environ.get("GRAPH_SYNC_JOB", "")
    if not JOB_NAME.fullmatch(job):
        raise ValueError("The sheet sync job is not configured for this server")
    body = {"overrides": {"containerOverrides": [{"env": [{"name": "GRAPH_SYNC_WORKSPACE", "value": workspace}]}]}}
    async with httpx.AsyncClient(timeout=TIMEOUTS.gateway_http, follow_redirects=False, trust_env=False) as http:
        response = await http.post(f"https://run.googleapis.com/v2/{job}:run", json=body,
                                   headers={"Authorization": f"Bearer {await _token()}"})
    response.raise_for_status()
    return response.json().get("name", "")
