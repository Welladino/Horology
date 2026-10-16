"""Document-graph sign-in: access from the users tables, a workspace chosen at sign-in and carried on the
tokens, resource-bound tokens and refused anonymous calls. No database or Google requests."""
import asyncio
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from mcp.server.auth.provider import AuthorizationParams, TokenError

from support.paths import DOCUMENT_GRAPH as GRAPH_ROOT  # noqa: E402
sys.path.append(str(GRAPH_ROOT))  # append: the gateway also has a top-level server.py

from document_graph.shared import workspace  # noqa: E402
from horology_runtime.access import Account, Directory  # noqa: E402
from horology_runtime.oauth.provider import GoogleOAuthProvider, GatewayCode  # noqa: E402
from support.oauth import MemoryStore, client  # noqa: E402

import importlib.util  # noqa: E402

URL = "https://graph.example.run.app"


def load_graph_server():
    # Loaded under its own name; the gateway's server.py is also importable as "server".
    spec = importlib.util.spec_from_file_location("document_graph_server", GRAPH_ROOT / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def reset_mode():
    yield
    workspace.configure(False)


class TableDirectory(Directory):
    """The real access rules and cache over an in-memory users table."""

    def __init__(self, accounts):
        super().__init__(None, "document-graph")
        self.accounts = accounts

    async def _fetch(self, email):
        return self.accounts.get(email)


ACCOUNTS = {
    "owner@example.com": Account(1, True, frozenset({"document-graph"}), ("client-x", "welladino")),
    "solo@example.com": Account(2, True, frozenset({"document-graph"}), ("welladino",)),
    "gateway-only@example.com": Account(3, True, frozenset({"gateway"}), ("welladino",)),
}


def graph_provider(accounts=None):
    directory = TableDirectory(accounts or ACCOUNTS)
    return GoogleOAuthProvider(MemoryStore(), URL, "google-client", "secret", scope="graph",
                               consent=lambda: ([], [], ""), check=directory.check, workspaces=directory.workspaces)


async def issued(provider, email, chosen):
    value = GatewayCode(code="c-" + email + chosen, scopes=["graph"], expires_at=time.time() + 120, client_id="client",
                        code_challenge="x", redirect_uri="http://localhost:9000/cb", redirect_uri_provided_explicitly=True,
                        resource=URL + "/mcp", subject="s", email=email, workspace=chosen, grant_id="g-" + email + chosen)
    await provider.store.put("code", value.code, value.model_dump(mode="json", exclude={"code"}), value.expires_at)
    return await provider.exchange_authorization_code(MagicMock(client_id="client"), value)


def test_local_mode_uses_environment_workspace(monkeypatch):
    monkeypatch.setenv("DOCUMENT_GRAPH_WORKSPACE", "job")
    assert workspace.current_workspace() == "job"


def test_signed_in_mode_reads_the_workspace_from_the_token(monkeypatch):
    workspace.configure(True)
    monkeypatch.setattr(workspace, "get_access_token", lambda: None)
    with pytest.raises(ValueError, match="Authentication required"):
        workspace.current_workspace()
    monkeypatch.setattr(workspace, "get_access_token", lambda: SimpleNamespace(claims={"workspace": "client-x"}))
    assert workspace.current_workspace() == "client-x"
    monkeypatch.setattr(workspace, "get_access_token", lambda: SimpleNamespace(claims={}))
    with pytest.raises(ValueError, match="reconnect"):
        workspace.current_workspace()


def test_tokens_carry_the_chosen_workspace_and_refused_accounts_get_none():
    provider = graph_provider()

    async def run():
        mine = await issued(provider, "owner@example.com", "client-x")
        token = await provider.load_access_token(mine.access_token)
        assert token.claims["workspace"] == "client-x" and token.claims["email"] == "owner@example.com"
        refreshed = await provider.exchange_refresh_token(MagicMock(client_id="client"),
                                                          await provider.load_refresh_token(None, mine.refresh_token), ["graph"])
        assert (await provider.load_access_token(refreshed.access_token)).claims["workspace"] == "client-x"
        for email, chosen in (("owner@example.com", "not-mine"), ("gateway-only@example.com", "welladino"),
                              ("stranger@example.com", "welladino")):
            with pytest.raises(TokenError):
                await issued(provider, email, chosen)
    asyncio.run(run())


def test_a_token_stops_working_when_membership_is_removed():
    accounts = dict(ACCOUNTS)
    provider = graph_provider(accounts)

    async def run():
        mine = await issued(provider, "owner@example.com", "client-x")
        accounts["owner@example.com"] = Account(1, True, frozenset({"document-graph"}), ("welladino",))
        provider.check.__self__.forget()  # as after the 5-minute cache expiry
        assert await provider.load_access_token(mine.access_token) is None
    asyncio.run(run())


def test_old_tokens_without_a_workspace_resolve_only_when_there_is_one():
    provider = graph_provider()

    async def run():
        solo = await issued(provider, "solo@example.com", "")
        assert (await provider.load_access_token(solo.access_token)).claims["workspace"] == "welladino"
        with pytest.raises(TokenError):
            await issued(provider, "owner@example.com", "")  # two workspaces: must reconnect and choose
    asyncio.run(run())


def test_consent_page_asks_for_a_workspace_when_there_are_several():
    from starlette.applications import Starlette
    from starlette.routing import Route
    provider = graph_provider()

    async def sign_in(http, email):
        params = AuthorizationParams(state="s", scopes=["graph"], code_challenge="c",
                                     redirect_uri="http://localhost:9000/callback", redirect_uri_provided_explicitly=True)
        start = await provider.authorize(client(), params)
        state = parse_qs(urlparse(start).query)["state"][0]
        await http.get(start)
        provider.verify_google = AsyncMock(return_value={"email": email, "sub": "subject"})
        return await http.get("/auth/google/callback", params={"state": state, "code": "google-code"})

    async def run():
        await provider.register_client(client().model_copy(update={"scope": "graph"}))
        app = Starlette(routes=[Route("/auth/google/start", provider.start), Route("/auth/google/callback", provider.callback),
                                Route("/auth/consent", provider.consent, methods=["POST"])])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=URL) as http:
            page = await sign_in(http, "owner@example.com")
            assert page.status_code == 200
            assert 'name="workspace" value="client-x" required' in page.text and "welladino" in page.text
            secret = http.cookies.get("horology_oauth")
            assert (await http.post("/auth/consent", data={"consent": secret, "decision": "allow"})).status_code == 400

            await sign_in(http, "owner@example.com")
            secret = http.cookies.get("horology_oauth")
            done = await http.post("/auth/consent", data={"consent": secret, "decision": "allow", "workspace": "client-x"})
            assert done.status_code == 303
            assert [v[0]["workspace"] for k, v in provider.store.data.items() if k[0] == "code"] == ["client-x"]

            solo = await sign_in(http, "solo@example.com")
            assert 'type="hidden" name="workspace" value="welladino"' in solo.text
            assert (await sign_in(http, "gateway-only@example.com")).status_code == 403
    asyncio.run(run())


def test_oauth_server_refuses_anonymous_calls_and_publishes_metadata(monkeypatch):
    monkeypatch.setenv("DOCUMENT_GRAPH_PUBLIC_URL", URL)
    server = load_graph_server()
    mcp = server.build_server(MagicMock(), {"client_id": "google-client", "client_secret": "secret"})
    app = mcp.streamable_http_app(stateless_http=True, json_response=True, host="0.0.0.0")

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=URL) as http:
            anonymous = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            assert anonymous.status_code == 401
            meta = (await http.get("/.well-known/oauth-authorization-server")).json()
            assert meta["issuer"].rstrip("/") == URL
            assert "graph" in meta["scopes_supported"]
    asyncio.run(run())
