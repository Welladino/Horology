"""Consent presentation: untrusted content is escaped and CSS is CSP hashed."""
import base64
import hashlib
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.oauth.consent_page import render_consent


def test_consent_escapes_identity_and_preserves_callback_policy():
    config = {"tools": ["github_read_file"], "repositories": ["Welladino/Horology"]}
    body, csp = render_consent('<script>alert(1)</script>', 'owner@example.com', '\"/><script>', config, {"repositories": config["repositories"]}, 'http://localhost:9000')
    assert '<script>' not in body
    assert '&lt;script&gt;' in body
    assert 'Welladino/Horology' in body
    css = re.search(r'<style>(.*?)</style>', body, re.S).group(1)
    digest = base64.b64encode(hashlib.sha256(css.encode()).digest()).decode()
    assert f"style-src 'sha256-{digest}'" in csp
    assert "form-action 'self' http://localhost:9000;" in csp
    assert "unsafe-inline" not in csp
    assert 'method="post" action="/auth/consent"' in body
