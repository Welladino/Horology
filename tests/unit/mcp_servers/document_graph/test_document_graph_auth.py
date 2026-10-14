"""Document-graph sign-in: workspace mapping, resource-bound tokens and refused anonymous calls."""
import asyncio
import sys
import time
from unittest.mock import MagicMock

import httpx
import pytest

from support.paths import DOCUMENT_GRAPH as GRAPH_ROOT  # noqa: E402
sys.path.append(str(GRAPH_ROOT))  # append: the gateway also has a top-level server.py

from document_graph.shared import workspace  # noqa: E402
from horology_runtime.oauth.provider import GoogleOAuthProvider, GatewayCode  # noqa: E402

import importlib.util  # noqa: E402


def load_graph_server():
    # Loaded under its own name; the gateway's server.py is also importable as "server".
    spec = importlib.util.spec_from_file_location("document_graph_server", GRAPH_ROOT / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def reset_workspaces():
    yield
    workspace.configure(None)


def test_mapping_is_case_insensitive_and_unmapped_email_is_refused():
    workspace.configure({"Owner@Example.com": "welladino", "job@example.com": "job"})
    assert workspace.workspace_for("owner@example.com") == "welladino"
    assert workspace.workspace_for("JOB@example.com") == "job"
    with pytest.raises(ValueError):
        workspace.workspace_for("stranger@example.com")


@pytest.mark.parametrize("mapping", [{}, {"no-at-sign": "w"}, {"a@b.c": " "}, ["a@b.c"]])
def test_invalid_mapping_is_rejected(mapping):
    with pytest.raises(ValueError):
        workspace.configure(mapping)


def test_local_mode_uses_environment_workspace(monkeypatch):
    monkeypatch.setenv("DOCUMENT_GRAPH_WORKSPACE", "job")
    assert workspace.current_workspace() == "job"


def test_signed_in_mode_requires_a_token():
    workspace.configure({"owner@example.com": "welladino"})
    with pytest.raises(ValueError, match="Authentication required"):
        workspace.current_workspace()


def test_oauth_server_refuses_anonymous_calls_and_publishes_metadata(monkeypatch):
    monkeypatch.setenv("DOCUMENT_GRAPH_PUBLIC_URL", "https://graph.example.run.app")
    server = load_graph_server()
    workspace.configure({"owner@example.com": "welladino"})
    mcp = server.build_server(MagicMock(), {"client_id": "google-client", "client_secret": "secret"})
    app = mcp.streamable_http_app(stateless_http=True, json_response=True, host="0.0.0.0")
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://graph.example.run.app") as http:
            anonymous = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            assert anonymous.status_code == 401
            meta = (await http.get("/.well-known/oauth-authorization-server")).json()
            assert meta["issuer"].rstrip("/") == "https://graph.example.run.app"
            assert "graph" in meta["scopes_supported"]
    asyncio.run(run())


class MemoryStore:
    def __init__(self):
        self.data = {}
    async def put(self, kind, key, value, expires):
        self.data[kind, key] = (value, expires)
    async def get(self, kind, key, consume=False):
        value = self.data.pop((kind, key), None) if consume else self.data.get((kind, key))
        return value[0] if value and value[1] > time.time() else None
    def grant_transaction(self):
        store = self
        class Context:
            async def __aenter__(self):
                return store
            async def __aexit__(self, *exc):
                return False
        return Context()


def test_tokens_carry_email_and_unmapped_accounts_are_refused():
    workspace.configure({"owner@example.com": "welladino"})
    provider = GoogleOAuthProvider(MemoryStore(), "https://graph.example.run.app", "google-client", "secret",
                                   scope="graph", consent=lambda: ([], [], ""), check=workspace.workspace_for)
    def code(email):
        return GatewayCode(code="c-" + email, scopes=["graph"], expires_at=time.time() + 120, client_id="client",
                           code_challenge="x", redirect_uri="http://localhost:9000/cb", redirect_uri_provided_explicitly=True,
                           resource="https://graph.example.run.app/mcp", subject="s", email=email, grant_id="g-" + email)
    async def run():
        for email in ("owner@example.com", "stranger@example.com"):
            value = code(email)
            await provider.store.put("code", value.code, value.model_dump(mode="json", exclude={"code"}), value.expires_at)
        mine = await provider.exchange_authorization_code(MagicMock(client_id="client"), code("owner@example.com"))
        token = await provider.load_access_token(mine.access_token)
        assert token.claims["email"] == "owner@example.com" and token.scopes == ["graph"]
        from mcp.server.auth.provider import TokenError
        with pytest.raises(TokenError):
            await provider.exchange_authorization_code(MagicMock(client_id="client"), code("stranger@example.com"))
    asyncio.run(run())
