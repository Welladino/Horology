"""
Container-level health/isolation test for the full Horology Docker
Compose projects (Hermes and the independent document-graph MCP).

Covers:
- Both independently started containers reach a running state
- The document graph MCP server is reachable only through a localhost port binding
- The document graph MCP server ARE reachable from inside the hermes container (the
  internal Docker network works, matching how Hermes actually connects)
- Hermes has exactly one host mount (hermes-data/), no others
- No container is running --privileged
- The Hermes dashboard requires auth (a bare request gets redirected,
  not served)

Unlike tests/mcp_servers/ (mocked, no Docker required), THIS suite
requires Docker Desktop running and `.env` populated with real
credentials - it drives the real `docker compose` CLI, same commands
used by hand throughout this project's development. Skipped
automatically if Docker isn't available or the stack fails to start,
rather than failing with a confusing low-level error.

Does NOT test real tool behavior (e.g. that write_document really
writes to Neon) - that's the "real end-to-end integration test" tier,
a separate, not-yet-built piece of work. This tier only proves the
containers themselves build, start, and stay correctly isolated from
each other and the host - the same properties verified by hand after
every docker-compose.yml change this project has made.

Source under test: docker-compose.yml and mcp-servers/document-graph/compose*.yaml
"""
import json
import subprocess
import time
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


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
    not _docker_available(),
    reason="Docker is not running or not installed - this suite drives the real docker compose stack.",
)


@pytest.fixture(scope="module")
def running_stack():
    """Bring the real stack up once for this module's tests, leave it
    running afterward (does NOT tear down - this project's containers
    are meant to stay up; tests shouldn't stop something the founder may
    be actively using)."""
    if not (REPO_ROOT / ".env").exists():
        pytest.skip(".env not found - container tests need real credentials to build/start the stack.")

    # Both MCP overlays share this network independently of Hermes's project name.
    inspected = subprocess.run(["docker", "network", "inspect", "horology_default"], capture_output=True, timeout=10)
    if inspected.returncode != 0:
        subprocess.run(["docker", "network", "create", "horology_default"], capture_output=True, timeout=10, check=True)
    # Ensure the official Hermes image is available on fresh machines.
    image = subprocess.run(["docker", "image", "inspect", "nousresearch/hermes-agent:latest"], capture_output=True, timeout=10)
    if image.returncode != 0:
        subprocess.run(["docker", "pull", "nousresearch/hermes-agent:latest"], capture_output=True, timeout=300, check=True)
    graph_files = ["-f", "mcp-servers/document-graph/compose.yaml", "-f", "mcp-servers/document-graph/compose.hermes-network.yaml"]
    build = _compose(*graph_files, "build", timeout=300)
    if build.returncode != 0:
        pytest.fail(f"docker compose build failed:\n{build.stderr}")

    up = _compose("up", "-d", timeout=120)
    if up.returncode != 0:
        pytest.fail(f"docker compose up failed:\n{up.stderr}")

    graph_up = _compose(*graph_files, "up", "-d", timeout=120)
    if graph_up.returncode != 0:
        pytest.fail(f"document-graph compose up failed:\n{graph_up.stderr}")

    # Wait for the existing Hermes dashboard instead of racing its startup.
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            response = httpx.get("http://localhost:9119/", timeout=2, follow_redirects=False)
            graph_ready = subprocess.run(
                ["docker", "exec", "horology-hermes", "curl", "-sS", "--max-time", "2",
                 "-o", "/dev/null", "-w", "%{http_code}", "-X", "POST",
                 "-H", "Content-Type: application/json",
                 "-H", "Accept: application/json, text/event-stream",
                 "-d", "{}", "http://document-graph-mcp:8765/mcp"],
                capture_output=True, text=True, timeout=5,
            )
            if response.status_code in (200, 302, 401) and graph_ready.stdout.strip() in ("400", "404", "406"):
                break
        except httpx.TransportError:
            pass
        time.sleep(0.5)
    else:
        pytest.fail("Hermes dashboard and document-graph did not become reachable within 30 seconds")
    yield


def _container_inspect(name: str) -> dict:
    result = subprocess.run(
        ["docker", "inspect", name], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"docker inspect {name} failed: {result.stderr}"
    return json.loads(result.stdout)[0]


@requires_docker
class TestContainersHealthy:
    @pytest.mark.parametrize(
        "container_name",
        ["horology-hermes", "horology-document-graph-mcp"],
    )
    def test_container_is_running(self, running_stack, container_name):
        info = _container_inspect(container_name)
        assert info["State"]["Running"] is True, f"{container_name} is not running: {info['State']}"

    @pytest.mark.parametrize(
        "container_name",
        ["horology-hermes", "horology-document-graph-mcp"],
    )
    def test_container_is_not_privileged(self, running_stack, container_name):
        info = _container_inspect(container_name)
        assert info["HostConfig"]["Privileged"] is False, f"{container_name} is running --privileged"


@requires_docker
class TestMountIsolation:
    def test_hermes_has_exactly_one_mount_scoped_to_hermes_data(self, running_stack):
        info = _container_inspect("horology-hermes")
        mounts = info["Mounts"]
        assert len(mounts) == 1, f"hermes has {len(mounts)} mounts, expected exactly 1: {mounts}"
        assert mounts[0]["Destination"] == "/opt/data"
        assert mounts[0]["Source"].endswith("hermes-data")

    @pytest.mark.parametrize(
        "container_name", ["horology-document-graph-mcp"]
    )
    def test_mcp_servers_have_no_host_mounts(self, running_stack, container_name):
        info = _container_inspect(container_name)
        assert info["Mounts"] == [], f"{container_name} has host mounts, expected none: {info['Mounts']}"


@requires_docker
class TestNetworkIsolation:
    def test_document_graph_mcp_published_only_on_localhost(self, running_stack):
        info = _container_inspect("horology-document-graph-mcp")
        bindings = info["HostConfig"]["PortBindings"]
        assert bindings == {"8765/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8765"}]}
        response = httpx.post("http://127.0.0.1:8765/mcp", json={},
                              headers={"Accept": "application/json, text/event-stream"}, timeout=5)
        assert response.status_code == 400


    def test_document_graph_mcp_reachable_from_hermes_container(self, running_stack):
        result = subprocess.run(
            ["docker", "exec", "horology-hermes", "curl", "-sS", "--max-time", "5",
             "-o", "/dev/null", "-w", "%{http_code}", "-X", "POST",
             "-H", "Content-Type: application/json",
             "-H", "Accept: application/json, text/event-stream",
             "-d", "{}", "http://document-graph-mcp:8765/mcp"],
            capture_output=True, text=True, timeout=15,
        )
        # 400 is expected (invalid JSON-RPC POST); a GET opens an event stream.
        # The bounded POST proves
        # network reachability, not an error. A connection failure (curl
        # exit code, no HTTP status at all) would mean the network is broken.
        assert result.stdout.strip() in ("400", "404", "406"), (
            f"Unexpected response reaching document-graph-mcp from hermes container: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )



@requires_docker
class TestDashboardAuth:
    def test_dashboard_requires_auth(self, running_stack):
        """A bare request (no credentials) must not return the dashboard
        content directly - either a redirect (302) or a 401, never 200."""
        resp = httpx.get("http://localhost:9119/", timeout=5, follow_redirects=False)
        assert resp.status_code in (302, 401), (
            f"Dashboard returned {resp.status_code} without credentials - expected a redirect or 401"
        )
