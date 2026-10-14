"""Consent presentation: untrusted content is escaped and CSS is CSP hashed."""
import base64
import hashlib
import re
import sys
from support.gateway import GATEWAY  # noqa: E402,F401  (puts the gateway on sys.path)
from horology_runtime.oauth.consent_page import render_consent
from shared.consent import NOTE, gateway_consent


def test_consent_escapes_identity_and_preserves_callback_policy():
    policy = {"access": {"tools": ["gateway_status", "supabase_list_schema"]}}
    sections, tools = gateway_consent(policy)
    body, csp = render_consent('<script>alert(1)</script>', 'owner@example.com', '\"/><script>', sections, tools, 'http://localhost:9000', NOTE)
    assert '<script>' not in body
    assert '&lt;script&gt;' in body
    assert 'Database metadata' in body
    css = re.search(r'<style>(.*?)</style>', body, re.S).group(1)
    digest = base64.b64encode(hashlib.sha256(css.encode()).digest()).decode()
    assert f"style-src 'sha256-{digest}'" in csp
    assert "form-action 'self' http://localhost:9000;" in csp
    assert "unsafe-inline" not in csp
    assert 'method="post" action="/auth/consent"' in body
