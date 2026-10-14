"""The gateway's bounded HTTP transport against real HTTP servers on 127.0.0.1, started by each test.

Checks httpx's actual behaviour, not our assumption about it: a redirect stops at the first host
(the token never reaches the second), and proxy settings in the environment are ignored. Each
check first shows that a client without our settings does the unsafe thing, so the test can fail.
No outside network."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from support.gateway import GATEWAY  # noqa: F401  (puts the gateway on sys.path)
from shared import http  # noqa: E402
from policy import Denied  # noqa: E402


class Server:
    """A local server that records each request and answers with respond(handler)."""
    def __init__(self, respond):
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                outer.requests.append({"path": self.path, "headers": dict(self.headers)})
                respond(self)
            do_POST = do_GET

            def log_message(self, *args):
                pass
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def servers():
    started = []

    def start(respond):
        server = Server(respond)
        started.append(server)
        return server
    yield start
    for server in started:
        server.close()


def json_reply(handler, data=None):
    body = json.dumps(data or {"ok": True}).encode()
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def test_a_redirect_stops_at_the_first_host_and_the_token_goes_nowhere_else(servers):
    elsewhere = servers(json_reply)

    def redirect(handler):
        handler.send_response(302)
        handler.send_header("Location", elsewhere.url + "/steal")
        handler.send_header("Content-Length", "0")
        handler.end_headers()
    first = servers(redirect)

    async def unsafe():  # control: a client that follows redirects reaches the second host
        async with httpx.AsyncClient(follow_redirects=True) as client:
            await client.get(first.url, headers={"Authorization": "Bearer control-token"})
    asyncio.run(unsafe())
    assert len(elsewhere.requests) == 1
    elsewhere.requests.clear()

    with pytest.raises(Denied, match="HTTP 302"):
        asyncio.run(http.request("GET", first.url, token="secret-token"))
    assert first.requests[-1]["headers"]["Authorization"] == "Bearer secret-token"
    assert elsewhere.requests == []  # never contacted, so it never saw the token


def test_proxy_settings_in_the_environment_are_ignored(servers, monkeypatch):
    target = servers(json_reply)
    proxy = servers(json_reply)  # would receive proxied requests
    for name in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.setenv(name, proxy.url)
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)

    async def unsafe():  # control: a client that trusts the environment goes through the proxy
        async with httpx.AsyncClient(trust_env=True) as client:
            await client.get(target.url + "/control")
    asyncio.run(unsafe())
    assert len(proxy.requests) == 1
    proxy.requests.clear()

    assert asyncio.run(http.request("GET", target.url + "/data", token="secret-token")) == {"ok": True}
    assert proxy.requests == [] and target.requests[-1]["path"] == "/data"


def test_a_large_reply_over_a_real_socket_is_refused(servers):
    def large(handler):  # 2 MB, sent in pieces
        handler.send_response(200)
        handler.send_header("Content-Length", str(2_000_000))
        handler.end_headers()
        try:
            for _ in range(200):
                handler.wfile.write(b"a" * 10_000)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the client hung up early, as it should
    server = servers(large)
    with pytest.raises(Denied, match="exceeds safe size limit"):
        asyncio.run(http.request("GET", server.url, token="secret-token"))
