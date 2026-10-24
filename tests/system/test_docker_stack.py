"""Container-level health and isolation checks for Horology's local MCP stack.

Hermes is built and tested in the separate Watchmaker repository. This module
owns only the document-graph container that is defined in Horology. It proves
that the container builds, starts without host mounts or privileged mode, and
publishes its MCP port on loopback only.

The suite needs Docker and the ignored document-graph environment file. It is
skipped automatically when either is unavailable. The fixture deliberately
leaves the service running because local development commonly keeps it alive.
"""

import json
import subprocess
import time

import httpx
import pytest

from support.paths import REPO as REPO_ROOT  # noqa: E402


GRAPH_FILES = (
    "-f",
    "mcp-servers/document-graph/compose.yaml",
    "-f",
    "mcp-servers/document-graph/compose.hermes-network.yaml",
)
GRAPH_ENV = REPO_ROOT / "mcp-servers" / "document-graph" / ".env"


def _docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _compose(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


requires_docker = pytest.mark.skipif(
    not _docker_available() or not GRAPH_ENV.is_file(),
    reason="Needs Docker and mcp-servers/document-graph/.env.",
)


@pytest.fixture(scope="module")
def running_graph():
    inspected = subprocess.run(
        ["docker", "network", "inspect", "horology_default"],
        capture_output=True,
        timeout=10,
    )
    if inspected.returncode != 0:
        subprocess.run(
            ["docker", "network", "create", "horology_default"],
            capture_output=True,
            timeout=10,
            check=True,
        )

    build = _compose(*GRAPH_FILES, "build", timeout=300)
    if build.returncode != 0:
        pytest.fail(f"document-graph compose build failed:\n{build.stderr}")

    up = _compose(*GRAPH_FILES, "up", "-d", timeout=120)
    if up.returncode != 0:
        pytest.fail(f"document-graph compose up failed:\n{up.stderr}")

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            response = httpx.post(
                "http://127.0.0.1:8765/mcp",
                json={},
                headers={"Accept": "application/json, text/event-stream"},
                timeout=2,
            )
            if response.status_code in (400, 404, 406):
                break
        except httpx.TransportError:
            pass
        time.sleep(0.5)
    else:
        pytest.fail("document-graph MCP did not become reachable within 30 seconds")

    yield


def _container_inspect(name: str) -> dict:
    result = subprocess.run(
        ["docker", "inspect", name], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"docker inspect {name} failed: {result.stderr}"
    return json.loads(result.stdout)[0]


@requires_docker
class TestDocumentGraphContainer:
    def test_is_running_and_not_privileged(self, running_graph):
        info = _container_inspect("horology-document-graph-mcp")
        assert info["State"]["Running"] is True
        assert info["HostConfig"]["Privileged"] is False

    def test_has_no_host_mounts(self, running_graph):
        info = _container_inspect("horology-document-graph-mcp")
        assert info["Mounts"] == []

    def test_mcp_port_is_published_only_on_loopback(self, running_graph):
        info = _container_inspect("horology-document-graph-mcp")
        bindings = info["HostConfig"]["PortBindings"]
        assert bindings == {"8765/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8765"}]}

        response = httpx.post(
            "http://127.0.0.1:8765/mcp",
            json={},
            headers={"Accept": "application/json, text/event-stream"},
            timeout=5,
        )
        assert response.status_code == 400
