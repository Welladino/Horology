"""
Container-level health/isolation test for the full Horology Docker
Compose stack (hermes, document-graph-mcp).

Covers:
- Both main-stack containers reach a running state after `docker compose up -d`
- The document graph MCP server is reachable from the host (no published port)
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

Source under test: docker-compose.yml
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

    build = _compose("build", timeout=300)
    if build.returncode != 0:
        pytest.fail(f"docker compose build failed:\n{build.stderr}")

    up = _compose("up", "-d", timeout=120)
    if up.returncode != 0:
        pytest.fail(f"docker compose up failed:\n{up.stderr}")

    # Give containers a moment to reach a stable running state.
    time.sleep(3)
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
    def test_document_graph_mcp_not_reachable_from_host(self, running_stack):
        with pytest.raises(httpx.ConnectError):
            httpx.get("http://localhost:8765/mcp", timeout=3)


    def test_document_graph_mcp_reachable_from_hermes_container(self, running_stack):
        result = subprocess.run(
            ["docker", "exec", "horology-hermes", "curl", "-sS", "-o", "/dev/null",
             "-w", "%{http_code}", "http://document-graph-mcp:8765/mcp"],
            capture_output=True, text=True, timeout=15,
        )
        # 400 is expected (bare GET without MCP session headers) - it proves
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
