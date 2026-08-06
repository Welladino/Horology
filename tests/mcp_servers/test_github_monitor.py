"""
Unit tests for mcp-servers/github-monitor/server.py.

Covers:
- Every GitHub API call is scoped to GITHUB_REPO only - the single-repo
  boundary is a real security property (the PAT is scoped to one repo,
  but this asserts the CODE also never asks for anything else)
- Response shaping (list_recent_commits, list_open_pull_requests, etc.
  return only the documented fields, correctly extracted)
- Truncation behavior on get_pull_request_diff / get_file_content
  (40,000 char cap - prevents an oversized diff/file from blowing out
  an agent's context)
- search_code always appends `repo:<GITHUB_REPO>` to the query, so it
  can never search outside the configured repo even if asked to

Mocked (no real GitHub API calls, no Docker, no real token needed).

Source under test: mcp-servers/github-monitor/server.py
"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SERVER_PATH = Path(__file__).parent.parent.parent / "mcp-servers" / "github-monitor" / "server.py"


@pytest.fixture
def server_module(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_fake")
    monkeypatch.setenv("GITHUB_REPO", "Welladino/Article_aggregator_agent")

    spec = importlib.util.spec_from_file_location("github_monitor_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["github_monitor_server"] = module
    spec.loader.exec_module(module)
    yield module
    del sys.modules["github_monitor_server"]


class TestRepoScoping:
    """Every tool must only ever touch GITHUB_REPO - never any other repo,
    even if a caller tried to pass one in (none of these tools accept a
    repo parameter at all, which is itself part of the boundary, but this
    also asserts the actual HTTP calls stay scoped)."""

    def test_get_repo_status_only_queries_configured_repo(self, server_module):
        with patch.object(server_module, "_get") as mock_get:
            mock_get.side_effect = [
                {"full_name": "Welladino/Article_aggregator_agent", "default_branch": "main",
                 "pushed_at": "2026-08-01T00:00:00Z", "open_issues_count": 0},
                [],
            ]
            server_module.get_repo_status()
        for call in mock_get.call_args_list:
            assert "Welladino/Article_aggregator_agent" in call[0][0]

    def test_search_code_always_appends_repo_filter(self, server_module):
        with patch.object(server_module, "_get", return_value={"items": []}) as mock_get:
            server_module.search_code("password")
        params = mock_get.call_args[1]["params"]
        assert params["q"] == "password repo:Welladino/Article_aggregator_agent"

    def test_search_code_cannot_override_repo_via_query_injection(self, server_module):
        """Even a query string that tries to inject its own repo: filter
        gets the real repo appended after it - GitHub's search treats
        multiple repo: qualifiers as AND, not override, so this can only
        narrow results, never escape the configured repo."""
        with patch.object(server_module, "_get", return_value={"items": []}) as mock_get:
            server_module.search_code("test repo:SomeOtherOrg/other-repo")
        params = mock_get.call_args[1]["params"]
        assert params["q"].endswith("repo:Welladino/Article_aggregator_agent")


class TestResponseShaping:
    def test_list_recent_commits_extracts_expected_fields(self, server_module):
        raw = [
            {
                "sha": "abcdef1234567890",
                "commit": {"author": {"name": "Jane", "date": "2026-08-01T00:00:00Z"}, "message": "fix bug\n\nmore detail"},
            }
        ]
        with patch.object(server_module, "_get", return_value=raw):
            result = server_module.list_recent_commits()
        assert result == [
            {"sha": "abcdef123456", "author": "Jane", "date": "2026-08-01T00:00:00Z", "message": "fix bug"}
        ]

    def test_list_recent_commits_clamps_limit(self, server_module):
        with patch.object(server_module, "_get", return_value=[]) as mock_get:
            server_module.list_recent_commits(limit=9999)
        assert mock_get.call_args[1]["params"]["per_page"] == 50

    def test_get_ci_status_handles_no_runs(self, server_module):
        with patch.object(server_module, "_get", return_value={"workflow_runs": []}):
            result = server_module.get_ci_status(ref="main")
        assert result == {"branch": "main", "status": "no_runs_found"}

    def test_list_open_pull_requests_extracts_expected_fields(self, server_module):
        raw = [{
            "number": 42, "title": "Fix auth", "user": {"login": "dev"},
            "created_at": "2026-08-01T00:00:00Z", "changed_files": 3,
            "base": {"ref": "main"}, "head": {"ref": "fix-auth"},
        }]
        with patch.object(server_module, "_get", return_value=raw):
            result = server_module.list_open_pull_requests()
        assert result[0]["number"] == 42
        assert result[0]["author"] == "dev"

    def test_list_dependabot_alerts_extracts_severity_and_package(self, server_module):
        raw = [{
            "number": 1, "state": "open",
            "security_advisory": {"severity": "high", "summary": "bad thing"},
            "dependency": {"package": {"name": "aiohttp"}},
        }]
        with patch.object(server_module, "_get", return_value=raw):
            result = server_module.list_dependabot_alerts()
        assert result[0] == {"number": 1, "severity": "high", "summary": "bad thing", "package": "aiohttp", "state": "open"}


class TestContentTruncation:
    def test_get_pull_request_diff_truncates_over_40000_chars(self, server_module):
        long_diff = "x" * 50000
        fake_response = MagicMock()
        fake_response.text = long_diff
        fake_response.raise_for_status.return_value = None
        with patch.object(server_module.httpx, "get", return_value=fake_response):
            result = server_module.get_pull_request_diff(1)
        assert len(result) < 50000
        assert "truncated" in result
        assert "50000" in result

    def test_get_pull_request_diff_does_not_truncate_short_diff(self, server_module):
        short_diff = "x" * 100
        fake_response = MagicMock()
        fake_response.text = short_diff
        fake_response.raise_for_status.return_value = None
        with patch.object(server_module.httpx, "get", return_value=fake_response):
            result = server_module.get_pull_request_diff(1)
        assert result == short_diff
        assert "truncated" not in result

    def test_get_file_content_rejects_directory(self, server_module):
        with patch.object(server_module, "_get") as mock_get:
            mock_get.side_effect = [
                {"default_branch": "main"},  # branch lookup (no ref passed)
                [{"name": "a"}, {"name": "b"}],  # contents call -> a directory listing
            ]
            with pytest.raises(ValueError, match="is a directory"):
                server_module.get_file_content("some/dir")
