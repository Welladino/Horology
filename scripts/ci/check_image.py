"""Runtime image contract; executes inside each built image without secrets."""
import importlib.util
import os
from pathlib import Path

assert os.getuid() == 10001, "MCP process must run as the dedicated non-root user"
assert importlib.util.find_spec("pip") is None, "Runtime image should not contain pip"
assert not Path("/app/.env").exists()
assert not Path("/app/.env.local").exists()
assert not Path("/app/config/policy.local.json").exists()
if Path("/app/policy.py").exists():
    import server
    from shared.oauth.consent_page import render_consent
    assert Path("/certs/supabase-ca.crt").is_file()
    assert Path("/app/shared/oauth/consent.css").is_file()
else:
    # Import-time configuration only; no connection or provider call is made.
    os.environ["DATABASE_URL_POOLED"] = "postgresql://test@127.0.0.1:1/test"
    import document_graph.tools
print("Runtime image contract passed")
