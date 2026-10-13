"""Live end-to-end check of the deployed Horology MCP services, with timing.

Signs in as a real MCP client (Google sign-in, once per service; tokens kept in
the git-ignored .auth/ folder), calls free tools twice to show cold and warm
timing, then lines up each call with the services' own Cloud Run and tool logs.

    .venv/bin/python scripts/ops/live_check.py            # free calls only
    .venv/bin/python scripts/ops/live_check.py --search   # + one paid embedding
    .venv/bin/python scripts/ops/live_check.py --sync     # + start the sheet sync job

Results print as a table and append to reports/live-checks.jsonl (git-ignored).
Log matching uses `gcloud --configuration=horology-view` (read-only).
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

import httpx2
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

ROOT = Path(__file__).resolve().parents[2]
AUTH_DIR = ROOT / ".auth"
REPORT = ROOT / "reports" / "live-checks.jsonl"
PROJECT, REGION = "horology-dev", "us-central1"
CALLBACK_PORT = 8976
SERVICES = {
    "mcp-gateway": {"url": "https://mcp-gateway-366292507424.us-central1.run.app/mcp", "scope": "gateway"},
    "document-graph": {"url": "https://document-graph-366292507424.us-central1.run.app/mcp", "scope": "graph"},
}


class FileTokenStorage(TokenStorage):
    """One owner-only JSON file per service, holding the client registration and tokens."""

    def __init__(self, name):
        AUTH_DIR.mkdir(mode=0o700, exist_ok=True)
        self.path = AUTH_DIR / f"{name}.json"

    def _load(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _save(self, data):
        self.path.write_text(json.dumps(data))
        os.chmod(self.path, 0o600)

    async def get_tokens(self):
        data = self._load().get("tokens")
        return OAuthToken.model_validate(data) if data else None

    async def set_tokens(self, tokens):
        data = self._load(); data["tokens"] = tokens.model_dump(mode="json"); data["saved_at"] = time.time()
        self._save(data)

    def expiry(self):
        """When the saved access token expires. The SDK doesn't persist this, so without it
        a new process sends an expired token, gets 401 and signs in again instead of refreshing."""
        data = self._load()
        lifetime = (data.get("tokens") or {}).get("expires_in")
        return data["saved_at"] + lifetime if lifetime and "saved_at" in data else None

    async def get_client_info(self):
        data = self._load().get("client")
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def set_client_info(self, client_info):
        data = self._load(); data["client"] = client_info.model_dump(mode="json"); self._save(data)


async def open_browser(url):
    print(f"\nSign in to continue (opening your browser):\n{url}\n", file=sys.stderr)
    webbrowser.open(url)


async def wait_for_callback():
    """Serve one request on the loopback callback and return its code and state."""
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            result.update(code=query.get("code", [None])[0], state=query.get("state", [None])[0],
                          error=query.get("error", [None])[0])
            self.send_response(200); self.send_header("Content-Type", "text/plain"); self.end_headers()
            self.wfile.write(b"Signed in. You can close this tab.")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", CALLBACK_PORT), Handler)
    thread = Thread(target=server.handle_request, daemon=True); thread.start()
    while thread.is_alive():
        await asyncio.sleep(0.2)
    server.server_close()
    if result.get("error") or not result.get("code"):
        raise RuntimeError(f"Sign-in did not complete: {result.get('error') or 'no code returned'}")
    return AuthorizationCodeResult(code=result["code"], state=result["state"])


def auth_for(name):
    spec = SERVICES[name]
    metadata = OAuthClientMetadata(
        client_name="Horology live check", redirect_uris=[f"http://127.0.0.1:{CALLBACK_PORT}/callback"],
        grant_types=["authorization_code", "refresh_token"], response_types=["code"],
        token_endpoint_auth_method="none", scope=spec["scope"])
    storage = FileTokenStorage(name)
    provider = OAuthClientProvider(spec["url"], metadata, storage,
                                   redirect_handler=open_browser, callback_handler=wait_for_callback)
    # Files saved before saved_at existed count as expired, so the refresh token is tried.
    provider.context.token_expiry_time = storage.expiry() or 1
    return provider


async def timed_session(name, calls):
    """Connect, then run each (label, tool, args) call; return per-step timings."""
    steps = []
    started = time.perf_counter()
    async with httpx2.AsyncClient(auth=auth_for(name), timeout=120) as http, \
            streamable_http_client(SERVICES[name]["url"], http_client=http) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            steps.append({"service": name, "step": "connect", "ms": round((time.perf_counter() - started) * 1000),
                          "ok": True, "at": now_iso()})
            for label, tool, args in calls:
                t0, at = time.perf_counter(), now_iso()
                result = await session.call_tool(tool, args)
                steps.append({"service": name, "step": label, "tool": tool, "at": at,
                              "ms": round((time.perf_counter() - t0) * 1000), "ok": not result.is_error})
    return steps


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ts(value):
    # Cloud Logging writes ...Z with nanoseconds; Python writes +00:00 with microseconds.
    value = value.replace("Z", "+00:00")
    if "." in value:
        head, rest = value.split(".", 1)
        frac, zone = rest[:rest.index("+")], rest[rest.index("+"):]
        value = f"{head}.{frac[:6]}{zone}"
    return datetime.fromisoformat(value)


def gcloud_logs(filter_, since):
    out = subprocess.run(
        ["gcloud", "--configuration=horology-view", "logging", "read", filter_, f"--project={PROJECT}",
         "--format=json", "--limit=200", "--freshness=1h"], capture_output=True, text=True)
    if out.returncode:
        return []
    return [e for e in json.loads(out.stdout or "[]") if ts(e["timestamp"]) >= ts(since)]


def attach_server_timing(steps, since):
    """Add tool-side duration and cold-start evidence from the services' logs."""
    tool_logs = gcloud_logs('resource.type="cloud_run_revision" AND jsonPayload.event="runtime_operation"', since)
    starts = gcloud_logs('resource.type="cloud_run_revision" AND textPayload:"Starting new instance"', since)
    cold = {e["resource"]["labels"]["service_name"] for e in starts}
    used = set()
    for step in steps:
        step["cold_start_in_window"] = step["service"] in cold
        if "tool" not in step:
            continue
        for entry in sorted(tool_logs, key=lambda e: ts(e["timestamp"])):
            p = entry.get("jsonPayload", {})
            key = p.get("request_id")
            if (entry["resource"]["labels"]["service_name"] == step["service"] and p.get("tool") == step["tool"]
                    and ts(entry["timestamp"]) >= ts(step["at"]) and key not in used):
                used.add(key)
                step["tool_ms"] = round(p.get("duration_ms", 0))
                step["outside_tool_ms"] = step["ms"] - step["tool_ms"]
                step["request_id"] = key
                break


def print_table(steps):
    print(f"\n{'service':<15}{'step':<24}{'total ms':>9}{'tool ms':>9}{'other ms':>9}  ok  cold-start-in-window")
    for s in steps:
        print(f"{s['service']:<15}{s['step']:<24}{s['ms']:>9}{s.get('tool_ms', ''):>9}{s.get('outside_tool_ms', ''):>9}"
              f"  {'yes' if s['ok'] else 'NO':<4}{'yes' if s.get('cold_start_in_window') else ''}")
    print("\n'tool ms' is time inside our code (from the service log); 'other ms' is network, sign-in checks,"
          " MCP overhead and any cold start.")


async def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--search", action="store_true", help="also call search_documents (one paid embedding)")
    parser.add_argument("--sync", action="store_true", help="also start the Document Index sync job")
    args = parser.parse_args()
    since = now_iso()
    gateway = [("gateway_status (1st)", "gateway_status", {}), ("gateway_status (2nd)", "gateway_status", {}),
               ("supabase_list_schema", "supabase_list_schema", {"schema": "public"})]
    graph = [("list_documents (1st)", "list_documents", {"limit": 5}), ("list_documents (2nd)", "list_documents", {"limit": 5})]
    if args.search:
        graph.append(("search_documents", "search_documents", {"query": "how do subscription agents pick up work", "limit": 3}))
    if args.sync:
        graph.append(("sync_graph", "sync_graph", {}))
    steps = []
    for name, calls in (("mcp-gateway", gateway), ("document-graph", graph)):
        try:
            steps += await timed_session(name, calls)
        except Exception as error:
            steps.append({"service": name, "step": "connect", "ms": 0, "ok": False, "at": now_iso(),
                          "error": type(error).__name__})
    print("\nWaiting 20 s for logs to arrive…", file=sys.stderr)
    await asyncio.sleep(20)
    attach_server_timing(steps, (datetime.fromisoformat(since) - timedelta(seconds=5)).isoformat())
    print_table(steps)
    REPORT.parent.mkdir(exist_ok=True)
    with REPORT.open("a") as f:
        f.write(json.dumps({"run_at": since, "steps": steps}) + "\n")
    print(f"\nSaved to {REPORT.relative_to(ROOT)}")
    return 0 if all(s["ok"] for s in steps) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
