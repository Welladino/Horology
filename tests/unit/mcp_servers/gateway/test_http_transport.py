"""The gateway's bounded HTTP transport (shared/http.py), with httpx's fake transport: no sockets.

What it promises: only a 200 is accepted, redirects are refused (never followed), a response
over MAX_BYTES is refused while it downloads, the token goes only in the Authorization header,
and environment proxies are ignored."""
import asyncio
import json

import httpx
import pytest

from support.gateway import GATEWAY  # noqa: F401  (puts the gateway on sys.path)
from shared import http  # noqa: E402
from policy import Denied  # noqa: E402

URL = "https://api.provider.example/v1/search"
REAL_CLIENT = httpx.AsyncClient


def serve(monkeypatch, handler):
    """Route the transport's client to handler; returns the client options and requests seen."""
    seen = {"options": None, "requests": []}

    def client(**options):
        seen["options"] = options
        return REAL_CLIENT(transport=httpx.MockTransport(lambda request: seen["requests"].append(request) or handler(request)),
                    **options)
    monkeypatch.setattr(httpx, "AsyncClient", client)
    return seen


def call(**kwargs):
    return asyncio.run(http.request(kwargs.pop("method", "POST"), URL, token="secret-token", **kwargs))


def test_a_200_json_reply_is_returned_and_the_token_goes_in_the_header(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, json={"results": [1, 2]}))
    assert call(body={"query": "x"}, params={"n": "5"}) == {"results": [1, 2]}
    request = seen["requests"][0]
    assert request.headers["Authorization"] == "Bearer secret-token"
    assert "secret-token" not in str(request.url) and json.loads(request.content) == {"query": "x"}
    assert request.url.params["n"] == "5"


def test_redirects_and_environment_proxies_are_off(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, json={}))
    call()
    assert seen["options"]["follow_redirects"] is False and seen["options"]["trust_env"] is False


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_a_redirect_is_refused_and_not_followed(monkeypatch, status):
    seen = serve(monkeypatch, lambda r: httpx.Response(status, headers={"Location": "https://attacker.example/steal"}))
    with pytest.raises(Denied, match=f"HTTP {status}"):
        call()
    assert len(seen["requests"]) == 1  # the Location was never requested


@pytest.mark.parametrize("status", [201, 204, 400, 401, 403, 404, 429, 500, 503])
def test_anything_but_200_is_refused_with_its_status(monkeypatch, status):
    serve(monkeypatch, lambda r: httpx.Response(status, json={"error": "no"}))
    with pytest.raises(Denied, match=f"HTTP {status}"):
        call()


def body_of(size):
    """A JSON reply of exactly size bytes ({"x": "aaa..."})."""
    body = json.dumps({"x": "a" * (size - 9)}).encode()
    assert len(body) == size
    return body


def test_a_reply_at_the_limit_is_accepted_and_one_byte_more_is_not(monkeypatch):
    serve(monkeypatch, lambda r: httpx.Response(200, content=body_of(http.MAX_BYTES)))
    assert len(call()["x"]) == http.MAX_BYTES - 9
    serve(monkeypatch, lambda r: httpx.Response(200, content=body_of(http.MAX_BYTES + 1)))
    with pytest.raises(Denied, match="exceeds safe size limit"):
        call()


def test_an_oversized_reply_is_refused_before_it_has_all_downloaded(monkeypatch):
    sent = []

    async def huge():  # 50 MB in 10 KB chunks, unless the reader stops
        for _ in range(5000):
            sent.append(1)
            yield b"a" * 10_000
    serve(monkeypatch, lambda r: httpx.Response(200, content=huge()))
    with pytest.raises(Denied, match="exceeds safe size limit"):
        call()
    assert len(sent) <= http.MAX_BYTES // 10_000 + 1  # stopped at about 150 KB, not 50 MB


def test_a_reply_that_isnt_json_fails(monkeypatch):
    serve(monkeypatch, lambda r: httpx.Response(200, content=b"<html>not json</html>"))
    with pytest.raises(json.JSONDecodeError):
        call()
