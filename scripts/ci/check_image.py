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
        ("horology_runtime.oauth.store", "OAuthRepository"),
    ):
        getattr(importlib.import_module(module), symbol)
    assert importlib.util.find_spec("integrations.github") is None
    assert importlib.util.find_spec("integrations.google_drive") is None
    assert not Path("/app/shared/writes.py").exists()
    getattr(importlib.import_module("horology_runtime.oauth.consent_page"), "render_consent")
    getattr(importlib.import_module("shared.consent"), "gateway_consent")
    assert Path("/certs/supabase-ca.crt").is_file()
    getattr(importlib.import_module("policy"), "load_policy")("/config/policy.json")
else:
    # Import-time configuration only; no connection or provider call is made.
    os.environ["DATABASE_URL_POOLED"] = "postgresql://test@127.0.0.1:1/test"
    importlib.import_module("document_graph.tools")
    # Shared graph logic is an installed package, not part of /app.
    for module in ("graph_core.documents.service", "graph_core.sections.service", "graph_core.ai.embeddings", "graph_core.ai.chat", "graph_core.runs.service"):
        importlib.import_module(module)
    # The sync job ships in the same image.
    importlib.import_module("graph_sync.sync")
    importlib.import_module("graph_sync.google")
# The shared consent stylesheet must be installed with the shared runtime.
assert (Path(importlib.import_module("horology_runtime").__file__).parent / "oauth" / "consent.css").is_file()
print("Runtime image contract passed")
