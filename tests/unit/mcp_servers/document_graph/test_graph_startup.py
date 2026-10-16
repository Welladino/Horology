"""Document-graph start-up decisions: sign-in settings, logging, and refusing an unmigrated database.
uvicorn is replaced, so nothing listens; the database pool is never opened."""
import asyncio
import importlib.util
import sys
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
import uvicorn

from support.paths import DOCUMENT_GRAPH

sys.path.append(str(DOCUMENT_GRAPH))  # append: the gateway also has a top-level server.py
import graph_core  # noqa: E402
from graph_core import database as graph_database  # noqa: E402
from document_graph.shared import workspace  # noqa: E402


def load_graph_server():
    spec = importlib.util.spec_from_file_location("document_graph_server_startup", DOCUMENT_GRAPH / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def started(monkeypatch):
    """Run main() with the given settings; returns uvicorn.run's keyword arguments."""
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))
    for name in ("DOCUMENT_GRAPH_OAUTH_ENABLED", "GOOGLE_OAUTH_CLIENT_ID",
                 "GOOGLE_OAUTH_CLIENT_SECRET", "DOCUMENT_GRAPH_PUBLIC_URL", "DOCUMENT_GRAPH_BIND", "PORT", "K_SERVICE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL_POOLED", "postgresql://unused@127.0.0.1:1/unused")

    def start(**settings):
        for name, value in settings.items():
            monkeypatch.setenv(name, value)
        load_graph_server().main()
        return calls[-1]
    yield start
    workspace.configure(False)


SIGN_IN = {"DOCUMENT_GRAPH_OAUTH_ENABLED": "true",
           "GOOGLE_OAUTH_CLIENT_ID": "client-id", "GOOGLE_OAUTH_CLIENT_SECRET": "client-secret",
           "DOCUMENT_GRAPH_PUBLIC_URL": "https://graph.example.run.app"}


def test_local_mode_starts_on_its_port_with_access_logs(started):
    options = started(DOCUMENT_GRAPH_BIND="127.0.0.1")
    assert (options["host"], options["port"], options["access_log"]) == ("127.0.0.1", 8765, True)


def test_cloud_run_port_is_used(started):
    assert started(PORT="8080", K_SERVICE="document-graph")["port"] == 8080


def test_sign_in_mode_starts_without_access_logs(started):
    # OAuth callback URLs carry short-lived codes, so request logs are off.
    assert started(**SIGN_IN)["access_log"] is False


@pytest.mark.parametrize("missing", ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"])
def test_sign_in_without_google_credentials_refuses_to_start(started, missing):
    with pytest.raises(ValueError, match="Google OAuth credentials are required"):
        started(**{**SIGN_IN, missing: ""})


def test_sign_in_with_a_plain_http_public_url_refuses_to_start(started):
    with pytest.raises(ValueError, match="must use HTTPS"):
        started(**{**SIGN_IN, "DOCUMENT_GRAPH_PUBLIC_URL": "http://graph.example.com"})


def test_without_a_database_url_it_refuses_to_start(started, monkeypatch):
    monkeypatch.delenv("DATABASE_URL_POOLED")
    with pytest.raises(ValueError, match="Database URL is not configured"):
        started()


def test_an_unmigrated_database_stops_start_up_before_serving(monkeypatch):
    events = []

    class FakeDatabase:
        async def __aenter__(self):
            events.append("open")
            return self

        async def __aexit__(self, *exc):
            events.append("close")

    async def not_ready():
        raise graph_database.NotReady("Document graph database is missing graph_runs: run alembic upgrade head")
    monkeypatch.setattr(graph_database, "check_ready", not_ready)

    @asynccontextmanager
    async def mcp_lifespan(app):
        events.append("serving")
        yield

    from starlette.applications import Starlette
    mcp = MagicMock()
    mcp.streamable_http_app.return_value = Starlette(lifespan=mcp_lifespan)
    app = load_graph_server().database_app(mcp, FakeDatabase())

    async def run():
        with pytest.raises(graph_database.NotReady, match="run alembic upgrade head"):
            async with app.router.lifespan_context(app):
                pass
    asyncio.run(run())
    assert events == ["open", "close"]  # never reached serving; the pool was closed
    graph_core.configure(None)
