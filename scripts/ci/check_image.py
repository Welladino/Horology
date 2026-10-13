"""Runtime image contract; executes inside each built image without secrets."""
import importlib
import importlib.util
import os
from pathlib import Path

assert os.getuid() == 10001, "MCP process must run as the dedicated non-root user"
assert importlib.util.find_spec("pip") is None, "Runtime image should not contain pip"
assert not Path("/app/.env").exists()
assert not Path("/app/.env.local").exists()
assert not Path("/app/config/policy.local.json").exists()
if Path("/app/policy.py").exists():
    # These modules belong to this image's /app, not scripts/ci. Runtime
    # imports deliberately verify the packaged modules and required symbols.
    importlib.import_module("server")
    for module, symbol in (
        ("database.connection", "Database"),
        ("database.repositories.quotas", "QuotaRepository"),
        ("database.repositories.cache", "CacheRepository"),
        ("database.repositories.oauth", "OAuthRepository"),
    ):
        getattr(importlib.import_module(module), symbol)
    assert importlib.util.find_spec("integrations.github") is None
    assert importlib.util.find_spec("integrations.google_drive") is None
    assert not Path("/app/shared/writes.py").exists()
    getattr(importlib.import_module("shared.oauth.consent_page"), "render_consent")
    assert Path("/certs/supabase-ca.crt").is_file()
    getattr(importlib.import_module("policy"), "load_policy")("/config/policy.json")
    assert Path("/app/shared/oauth/consent.css").is_file()
else:
    # Import-time configuration only; no connection or provider call is made.
    os.environ["DATABASE_URL_POOLED"] = "postgresql://test@127.0.0.1:1/test"
    importlib.import_module("document_graph.tools")
print("Runtime image contract passed")
