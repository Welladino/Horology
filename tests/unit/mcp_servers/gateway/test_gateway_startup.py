"""Gateway start-up decisions: credentials it must have, and how it listens.
uvicorn is replaced, so nothing listens; the database pool is never opened."""
import pytest
import uvicorn

from support.gateway import GATEWAY
import server  # noqa: E402  (the gateway's server.py, on sys.path via support.gateway)
from policy import Denied  # noqa: E402

DIGEST = "a" * 64  # a SHA-256 hex digest's shape


@pytest.fixture
def started(monkeypatch):
    """Run main() with the given settings; returns uvicorn.run's keyword arguments."""
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))
    for name in ("GATEWAY_OAUTH_ENABLED", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "GATEWAY_PUBLIC_URL",
                 "GATEWAY_BIND", "PORT", "K_SERVICE", "GATEWAY_TOKEN_HASHES"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GATEWAY_POLICY", str(GATEWAY / "config/policy.example.json"))
    monkeypatch.setenv("GATEWAY_DATABASE_URL", "postgresql://unused@127.0.0.1:1/unused")

    def start(**settings):
        for name, value in settings.items():
            monkeypatch.setenv(name, value)
        server.main()
        return calls[-1]
    return start


def test_local_bearer_mode_listens_on_localhost_without_access_logs(started):
    options = started(GATEWAY_TOKEN_HASHES=f'["{DIGEST}"]')
    assert (options["host"], options["port"], options["access_log"]) == ("127.0.0.1", 8767, False)


def test_google_sign_in_mode_starts_without_local_tokens(started):
    assert started(GATEWAY_OAUTH_ENABLED="true", GOOGLE_OAUTH_CLIENT_ID="id", GOOGLE_OAUTH_CLIENT_SECRET="secret",
                   GATEWAY_PUBLIC_URL="https://gateway.example.run.app")["access_log"] is False


@pytest.mark.parametrize("hashes", ["[]", '"not-a-list"', '["short"]', f'["{DIGEST}", 7]'])
def test_without_valid_hashed_tokens_or_sign_in_it_refuses_to_start(started, hashes):
    with pytest.raises(Denied, match="Provision hashed local credentials"):
        started(GATEWAY_TOKEN_HASHES=hashes)


def test_sign_in_without_google_credentials_refuses_to_start(started):
    with pytest.raises(ValueError, match="Google OAuth credentials are required"):
        started(GATEWAY_OAUTH_ENABLED="true", GATEWAY_PUBLIC_URL="https://gateway.example.run.app")


def test_without_a_database_url_it_refuses_to_start(started, monkeypatch):
    monkeypatch.delenv("GATEWAY_DATABASE_URL")
    with pytest.raises(Denied, match="GATEWAY_DATABASE_URL is not configured"):
        started(GATEWAY_TOKEN_HASHES=f'["{DIGEST}"]')


def test_an_unknown_policy_file_refuses_to_start(started, monkeypatch, tmp_path):
    monkeypatch.setenv("GATEWAY_POLICY", str(tmp_path / "missing.json"))
    with pytest.raises(FileNotFoundError):
        started(GATEWAY_TOKEN_HASHES=f'["{DIGEST}"]')
