"""Start one sync job execution for one workspace, in one mode; nothing else in Cloud Run is reachable.

Used by the MCP service (sync_graph, rebuild_topics) and by the job itself to
start a follow-up run. GRAPH_SYNC_JOB is the job's full name in both."""
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


MODES = ("sync", "entities", "topics")


async def start(workspace, mode="sync", chain=1, token=""):
    """mode: "sync" imports the Document Index (then entities); "entities" runs the entity step only;
    "topics" re-clusters the workspace's topics. chain: this run's place in a chain of follow-ups;
    token: identifies the workspace claim taken for this run, which the job confirms."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    job = os.environ.get("GRAPH_SYNC_JOB", "")
    if not JOB_NAME.fullmatch(job):
        raise ValueError("The sheet sync job is not configured for this server")
    env = [{"name": "GRAPH_SYNC_WORKSPACE", "value": workspace}, {"name": "GRAPH_SYNC_MODE", "value": mode},
           {"name": "GRAPH_SYNC_CHAIN", "value": str(int(chain))}, {"name": "GRAPH_RUN_TOKEN", "value": token}]
    body = {"overrides": {"containerOverrides": [{"env": env}]}}
    async with httpx.AsyncClient(timeout=TIMEOUTS.gateway_http, follow_redirects=False, trust_env=False) as http:
        response = await http.post(f"https://run.googleapis.com/v2/{job}:run", json=body,
                                   headers={"Authorization": f"Bearer {await _token()}"})
    response.raise_for_status()
    return response.json().get("name", "")
