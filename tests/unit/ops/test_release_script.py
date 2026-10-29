"""scripts/ops/gcp/release.sh in --dry-run mode: which commands a release runs, without gcloud."""
import subprocess

import pytest

from support.paths import REPO

SCRIPT = REPO / "scripts" / "ops" / "gcp" / "release.sh"
REGISTRY = "us-central1-docker.pkg.dev/horology-dev/mcp-servers"


def dry_run(*args):
    return subprocess.run(
        ["bash", str(SCRIPT), "--dry-run", *args], cwd=REPO, capture_output=True, text=True, check=False
    )


def test_script_parses():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_document_graph_deploys_service_and_job_by_digest_only():
    result = dry_run("document-graph")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert f"run services update document-graph --region=us-central1 --image={REGISTRY}/document-graph@sha256:" in out
    assert "--configuration=horology-admin run jobs update document-graph-sync" in out
    assert "services update mcp-gateway" not in out
    assert ":latest" not in out
    assert "upgrade head" not in out


def test_all_deploys_both_services():
    out = dry_run("all").stdout
    assert "run services update mcp-gateway" in out
    assert "run services update document-graph" in out


def test_migrate_flag_runs_upgrade():
    assert "alembic upgrade head" in dry_run("--migrate", "gateway").stdout


@pytest.mark.parametrize("args", [(), ("bogus",), ("gateway", "all")])
def test_bad_arguments_fail(args):
    assert dry_run(*args).returncode != 0
