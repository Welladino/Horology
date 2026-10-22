"""Bounded Pages publishing; no calls to Cloudflare."""
import asyncio
import base64
import json

import httpx
import pytest

from support.gateway import GATEWAY  # noqa: F401  (sets import path)
from integrations.cloudflare import client
from integrations.cloudflare import protection, tools
from policy import Denied


def test_publisher_rejects_unsafe_assets():
    for path in ("../secret.png", ".env", "assets//chart.png", "script.js", "index.html"):
        with pytest.raises(Denied):
            client._files("<h1>Hi</h1>", [{"path": path, "base64": base64.b64encode(b"x").decode()}])
    with pytest.raises(Denied):
        client._files("x" * (client.MAX_HTML + 1), [])


def test_publish_uploads_only_to_pipeline_preview(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_PAGES_API_TOKEN", "test-token")
    calls = []
    real_async_client = httpx.AsyncClient

    def respond(request):
        path = request.url.path
        calls.append((request.method, path, request.headers, request.content))
        if path.endswith("/upload-token"):
            result = {"jwt": "short-lived-test-jwt"}
        elif path == "/client/v4/pages/assets/check-missing":
            hashes = json.loads(request.content)["hashes"]
            result = hashes
        elif path == "/client/v4/pages/assets/upload":
            payload = json.loads(request.content)
            assert all(item["base64"] and item["metadata"]["contentType"] for item in payload)
            result = True
        elif path == "/client/v4/pages/assets/upsert-hashes":
            return httpx.Response(200, json={"success": True})
        elif path.endswith("/deployments") and request.method == "POST":
            form = request.content.decode()
            assert 'pipeline-22' in form
            assert '/index.html' in form and '/assets/chart.svg' in form
            assert 'main' not in form
            result = {"id": "deployment-1"}
        elif path.endswith("/deployments/deployment-1"):
            result = {"id": "deployment-1", "latest_stage": {"status": "success"}}
        else:
            raise AssertionError(path)
        return httpx.Response(200, json={"success": True, "result": result})

    def mock_client(**kwargs):
        return real_async_client(transport=httpx.MockTransport(respond), **kwargs)

    monkeypatch.setattr(client.httpx, "AsyncClient", mock_client)
    result = asyncio.run(client.publish(
        22, "<h1>Decision</h1>",
        [{"path": "assets/chart.svg", "base64": base64.b64encode(b"<svg/>").decode()}],
        "horology-synthesis",
    ))
    assert result["url"] == "https://pipeline-22.horology-synthesis.pages.dev/"
    assert result["file_count"] == 2
    upload = next(row for row in calls if row[1].endswith("/assets/upload"))
    assert upload[2]["authorization"] == "Bearer short-lived-test-jwt"
    assert all("test-token" not in str(row[3]) for row in calls)


def test_publish_requires_numeric_pipeline_id():
    with pytest.raises(Denied):
        asyncio.run(client.publish(True, "<h1>Hi</h1>", [], "horology-synthesis"))


def test_publisher_requires_google_claim():
    from types import SimpleNamespace
    assert tools.publisher_email(SimpleNamespace(claims={"email": "Owner@Example.com"})) == "owner@example.com"
    with pytest.raises(Denied):
        tools.publisher_email(SimpleNamespace(claims={}))
    with pytest.raises(Denied):
        tools.publisher_email(None)


def test_access_rejects_broad_or_missing_policy():
    with pytest.raises(protection.ProtectionNotReady):
        protection._exact_emails([])
    with pytest.raises(protection.ProtectionNotReady):
        protection._exact_emails([{"decision": "allow", "include": [{"everyone": {}}]}])
    with pytest.raises(protection.ProtectionNotReady):
        protection._exact_emails([{"decision": "bypass", "include": [{"email": {"email": "a@example.com"}}]}])
    assert protection._exact_emails([{"decision": "allow", "include": [{"email": {"email": "A@example.com"}}]}]) == {"a@example.com"}


@pytest.mark.parametrize('separate_access_token', [False, True])
def test_access_verifies_both_pages_hostnames_and_members(monkeypatch, separate_access_token):
    monkeypatch.setenv("CLOUDFLARE_PAGES_API_TOKEN", "test-pages-token")
    if separate_access_token:
        monkeypatch.setenv("CLOUDFLARE_ACCESS_API_TOKEN", "test-access-token")
    else:
        monkeypatch.delenv("CLOUDFLARE_ACCESS_API_TOKEN", raising=False)
    real_async_client = httpx.AsyncClient
    paths = []

    def respond(request):
        path = request.url.path
        paths.append(path)
        expected_token = "test-access-token" if separate_access_token and "/access/" in path else "test-pages-token"
        assert request.headers["authorization"] == f"Bearer {expected_token}"
        if path.endswith("/pages/projects/horology-client-x"):
            value = {"name": "horology-client-x"}
        elif path.endswith("/access/apps/main-app"):
            value = {"type": "self_hosted", "domain": "horology-client-x.pages.dev"}
        elif path.endswith("/access/apps/preview-app"):
            value = {"type": "self_hosted", "domain": "*.horology-client-x.pages.dev"}
        elif path.endswith("/access/apps/main-app/policies") or path.endswith("/access/apps/preview-app/policies"):
            value = [{"id": "exact-email", "decision": "allow",
                      "include": [{"email": {"email": "personal@example.com"}}]}]
        else:
            raise AssertionError(path)
        return httpx.Response(200, json={"success": True, "result": value})

    monkeypatch.setattr(protection.httpx, "AsyncClient", lambda **kwargs: real_async_client(transport=httpx.MockTransport(respond), **kwargs))
    mapping = {"project": "horology-client-x", "main_app_id": "main-app", "preview_app_id": "preview-app", "enabled": True}
    asyncio.run(protection.ensure_private(mapping, {"personal@example.com"}, "personal@example.com"))
    assert len(paths) == 5
    with pytest.raises(protection.ProtectionNotReady):
        asyncio.run(protection.ensure_private(mapping, {"owner@example.com"}, "personal@example.com"))


def test_second_workspace_without_access_returns_admin_message_before_upload(monkeypatch):
    from types import SimpleNamespace

    class Mcp:
        fn = None

        def tool(self):
            def register(fn):
                self.fn = fn
                return fn
            return register

    class Access:
        def scope(self, tool):
            return "client-2", {}

        async def reserve(self, *args):
            raise AssertionError("Unprotected publication must not reserve or upload")

    class Directory:
        async def workspaces(self, email):
            assert email == "personal@example.com"
            return ["personal-test"]

    class Pages:
        async def get(self, workspace):
            assert workspace == "personal-test"
            return None

    monkeypatch.setattr(tools, "get_access_token", lambda: SimpleNamespace(claims={"email": "personal@example.com"}))
    monkeypatch.setattr(tools, "current_client_id", lambda: "client-2")
    mcp = Mcp()
    tools.register_tools(mcp, Access(), Directory(), Pages())
    result = asyncio.run(mcp.fn(22, "<h1>Private</h1>"))
    assert result["status"] == "needs_admin_setup"
    assert "Cloudflare administrator" in result["message"]


def test_second_workspace_publishes_only_to_its_own_project(monkeypatch):
    from types import SimpleNamespace

    class Mcp:
        fn = None

        def tool(self):
            def register(fn):
                self.fn = fn
                return fn
            return register

    class Access:
        def scope(self, tool):
            return "client-2", {}

        async def reserve(self, *args):
            assert args[0] == "client-2"

    class Directory:
        async def workspaces(self, email):
            return ["personal-test"]

    class Pages:
        async def get(self, workspace):
            return {"project": "horology-personal-test", "main_app_id": "main", "preview_app_id": "preview", "enabled": True}

        async def viewers(self, workspace):
            return {"personal@example.com"}

    async def protected(mapping, members, caller):
        assert mapping["project"] == "horology-personal-test"
        assert caller in members

    async def published(pipeline_id, html, assets, project):
        assert project == "horology-personal-test"
        return {"url": "https://pipeline-22.horology-personal-test.pages.dev/"}

    monkeypatch.setattr(tools, "get_access_token", lambda: SimpleNamespace(claims={"email": "personal@example.com"}))
    monkeypatch.setattr(tools, "current_client_id", lambda: "client-2")
    monkeypatch.setattr(protection, "ensure_private", protected)
    monkeypatch.setattr(client, "publish", published)
    mcp = Mcp()
    tools.register_tools(mcp, Access(), Directory(), Pages())
    result = asyncio.run(mcp.fn(22, "<h1>Private</h1>"))
    assert result == {"status": "published", "workspace": "personal-test",
                      "url": "https://pipeline-22.horology-personal-test.pages.dev/"}


def test_access_failure_returns_admin_message_without_upload(monkeypatch):
    from types import SimpleNamespace

    class Mcp:
        fn = None

        def tool(self):
            def register(fn):
                self.fn = fn
                return fn
            return register

    class Access:
        def scope(self, tool):
            return "client-2", {}

        async def reserve(self, *args):
            raise AssertionError("Access failure must not reserve")

    class Directory:
        async def workspaces(self, email):
            return ["personal-test"]

    class Pages:
        async def get(self, workspace):
            return {"project": "horology-personal-test", "main_app_id": "main", "preview_app_id": "preview", "enabled": True}

        async def viewers(self, workspace):
            return {"personal@example.com"}

    async def unprotected(*args):
        raise protection.ProtectionNotReady()

    monkeypatch.setattr(tools, "get_access_token", lambda: SimpleNamespace(claims={"email": "personal@example.com"}))
    monkeypatch.setattr(tools, "current_client_id", lambda: "client-2")
    monkeypatch.setattr(protection, "ensure_private", unprotected)
    mcp = Mcp()
    tools.register_tools(mcp, Access(), Directory(), Pages())
    result = asyncio.run(mcp.fn(22, "<h1>Private</h1>"))
    assert result["status"] == "needs_admin_setup"
    assert "Cloudflare Access" in result["message"]
