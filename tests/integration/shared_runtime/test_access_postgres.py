"""Users, workspaces and MCP access against a disposable migrated Postgres: the admin script writes them
as the owner, and both service logins read them through the shared access lookup."""
import asyncio
import importlib.util
import os
import uuid
from types import SimpleNamespace

import psycopg
import pytest

from horology_runtime.access import AccessDenied, Directory
from horology_runtime.database import Database
from support.paths import REPO

TAG = uuid.uuid4().hex[:8]
OWNER, OTHER = f"owner-{TAG}@example.com", f"other-{TAG}@example.com"
WS_A, WS_B, SERVER = f"ws-a-{TAG}", f"ws-b-{TAG}", f"test-server-{TAG}"


def load_admin():
    spec = importlib.util.spec_from_file_location("access_admin", REPO / "scripts" / "ops" / "access.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup():
    owner = os.environ.get("GATEWAY_TEST_DATABASE_URL")
    graph, gateway = os.environ.get("GRAPH_TEST_RUNTIME_URL"), os.environ.get("GATEWAY_TEST_RUNTIME_URL")
    if not (owner and graph and gateway):
        pytest.skip("Disposable migrated Postgres with the owner, horology_graph and horology_gateway logins is required")
    admin = load_admin()
    with psycopg.connect(owner) as conn:
        admin.server_add(conn, SERVER, "Test server")
        admin.workspace_add(conn, WS_A, "A", index="index-a", pipeline="pipe-a")
        admin.workspace_add(conn, WS_B, "B")
        for email in (OWNER, OTHER):
            admin.user_add(conn, email.upper())  # stored lowercase
        admin.member_add(conn, OWNER, WS_A, "owner")
        admin.member_add(conn, OWNER, WS_B)
        admin.member_add(conn, OTHER, WS_A)
        admin.grant(conn, OWNER, "document-graph")
        admin.grant(conn, OWNER, "gateway")
        admin.grant(conn, OTHER, SERVER)
    yield SimpleNamespace(admin=admin, owner=owner, graph=graph, gateway=gateway)
    with psycopg.connect(owner) as conn:
        conn.execute("DELETE FROM access.users WHERE email IN (%s, %s)", (OWNER, OTHER))
        conn.execute("DELETE FROM access.workspaces WHERE name IN (%s, %s)", (WS_A, WS_B))
        conn.execute("DELETE FROM access.mcp_servers WHERE id = %s", (SERVER,))


def lookup(dsn, server, body):
    async def run():
        async with Database(dsn, 2) as db:
            return await body(Directory(db, server))
    return asyncio.run(run())


def test_both_logins_read_access_and_workspaces(setup):
    async def graph(directory):
        assert await directory.workspaces(OWNER) == sorted([WS_A, WS_B])
        assert await directory.check(OWNER, WS_B) == WS_B
        with pytest.raises(AccessDenied):
            await directory.check(OTHER, WS_A)  # a member, but not granted document-graph
    lookup(setup.graph, "document-graph", graph)

    async def gateway(directory):
        assert await directory.check(OWNER) is None
        with pytest.raises(AccessDenied):
            await directory.check(OTHER)
    lookup(setup.gateway, "gateway", gateway)


def test_disabling_a_server_workspace_or_user_takes_effect(setup):
    admin = setup.admin
    with psycopg.connect(setup.owner) as conn:
        admin.workspace_active(conn, WS_B, False)
        admin.server_active(conn, SERVER, False)

    async def after(directory):
        assert await directory.workspaces(OWNER) == [WS_A]  # inactive workspaces are hidden
        return directory
    lookup(setup.graph, "document-graph", after)

    async def server_off(directory):
        with pytest.raises(AccessDenied):
            await directory.check(OTHER)  # granted, but the server is disabled
    lookup(setup.graph, SERVER, server_off)

    with psycopg.connect(setup.owner) as conn:
        admin.user_active(conn, OWNER, False)

    async def user_off(directory):
        with pytest.raises(AccessDenied):
            await directory.check(OWNER, WS_A)
    lookup(setup.gateway, "document-graph", user_off)


def test_the_database_refuses_bad_grants_and_lists_read_back(setup):
    admin = setup.admin
    with psycopg.connect(setup.owner) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            admin.grant(conn, OWNER, "gatway")  # a typo is refused: no such server
    with psycopg.connect(setup.owner) as conn:
        with pytest.raises(admin.AdminError, match="No user"):
            admin.grant(conn, "nobody@example.com", "gateway")
        email, active, servers, workspaces, _ = admin.user_show(conn, OWNER)
        assert (email, active, servers) == (OWNER, True, "document-graph, gateway")
        assert workspaces == f"{WS_A} (owner), {WS_B} (member)"
        admin.revoke(conn, OWNER, "gateway")
        admin.member_remove(conn, OWNER, WS_B)
        assert admin.user_show(conn, OWNER)[2:4] == ("document-graph", f"{WS_A} (owner)")
    with psycopg.connect(setup.owner) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute("DELETE FROM access.mcp_servers WHERE id = 'document-graph'")  # still granted: disable instead


def test_the_sync_job_reads_workspace_spreadsheets(setup):
    import sys
    from support.paths import SYNC_JOB
    sys.path.append(str(SYNC_JOB))
    from graph_sync.__main__ import configured_workbooks

    async def run():
        async with Database(setup.graph, 2) as db:
            return await configured_workbooks(db)
    books = asyncio.run(run())
    assert books[WS_A] == {"index": "index-a", "pipeline": "pipe-a"}
    assert WS_B not in books  # no Document Index: nothing to sync
