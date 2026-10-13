"""Escaped consent presentation with a hash-authorized stylesheet.

Each service describes what a connection can do as (title, text) sections;
this module only renders and escapes them.
"""
import base64
import hashlib
import html
from pathlib import Path


def render_consent(client, email, secret, sections, tools, callback_origin, note):
    css = Path(__file__).with_name("consent.css").read_text()
    esc = lambda value: html.escape(str(value), quote=True)
    cards = "".join(f"<li><strong>{esc(title)}</strong><p>{esc(text)}</p></li>" for title, text in sections)
    names = "".join(f"<li><code>{esc(t)}</code></li>" for t in tools)
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Authorize Horology access</title><style>{css}</style></head><body><main><p class="brand">HOROLOGY</p><h1>Authorize Horology access</h1><p class="intro">Connect <strong>{esc(client)}</strong> to your approved tools.</p><div class="account"><span>Signed in as</span><strong>{esc(email)}</strong></div><h2>What this connection can do</h2><ul class="permissions">{cards}</ul><p class="note">{esc(note)}</p><details><summary>View approved tool names</summary><ul class="tools">{names}</ul></details><form method="post" action="/auth/consent"><input type="hidden" name="consent" value="{esc(secret)}"><button class="allow" name="decision" value="allow">Allow access</button><button class="deny" name="decision" value="deny">Cancel</button></form><p class="footer">Only continue if you started this connection in {esc(client)}.</p></main></body></html>"""
    digest = base64.b64encode(hashlib.sha256(css.encode()).digest()).decode()
    csp = f"default-src 'none'; style-src 'sha256-{digest}'; form-action 'self' {callback_origin}; frame-ancestors 'none'; base-uri 'none'"
    return body, csp
