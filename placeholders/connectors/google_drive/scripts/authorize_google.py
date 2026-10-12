"""One-time local Google provider OAuth. Save refresh credentials privately, never print them."""
import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import httpx
import jwt
from dotenv import dotenv_values
from horology_runtime.settings import TIMEOUTS, OAUTH

REDIRECT = 'http://localhost:8768/callback'
SCOPES = ['openid','email','https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/drive.file']


def save_credentials(path, values):
    original = path.read_text() if path.exists() else ''
    names = set(values)
    lines = [line for line in original.splitlines() if line.split('=',1)[0].strip() not in names]
    lines.extend(key+'='+json.dumps(value) for key,value in values.items())
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.google-oauth-')
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as out:
            out.write('\n'.join(lines)+'\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file',type=Path,default=Path(__file__).resolve().parents[1]/'.env.local')
    parser.add_argument('--email',default='saravanaraj.subramaniam@welladino.com')
    parser.add_argument('--registers', action='store_true', help='Request Sheets scope for bounded existing-register writes')
    args = parser.parse_args()
    scopes = SCOPES + (['https://www.googleapis.com/auth/spreadsheets'] if args.registers else [])
    env = dotenv_values(args.env_file)
    client_id = env.get('GOOGLE_DRIVE_CLIENT_ID') or env.get('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = env.get('GOOGLE_DRIVE_CLIENT_SECRET') or env.get('GOOGLE_OAUTH_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise SystemExit('Save Google OAuth client credentials in the private environment first.')
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    result = {}
    class Callback(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path != '/callback' or not hmac.compare_digest(query.get('state',[''])[0],state):
                self.send_response(400);self.end_headers();self.wfile.write(b'Invalid OAuth callback.');return
            result.update(code=query.get('code',[''])[0],error=query.get('error',[''])[0])
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('Referrer-Policy','no-referrer')
            self.end_headers();self.wfile.write(b'Google authorization received. You may close this window; check the local setup result.')
    # Never bind the authorization callback to public interfaces.
    with HTTPServer(('127.0.0.1',8768),Callback) as server:
        server.timeout = 1
        url = 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':client_id,'redirect_uri':REDIRECT,'response_type':'code','scope':' '.join(scopes),'access_type':'offline','prompt':'consent','state':state,'nonce':nonce,'code_challenge':challenge,'code_challenge_method':'S256','login_hint':args.email})
        print('Authorize Google provider access using this URL:',flush=True)
        print(url,flush=True)
        deadline = time.monotonic()+OAUTH.login_seconds
        while not result and time.monotonic()<deadline:
            server.handle_request()
    if not result.get('code') or result.get('error'):
        raise SystemExit('Authorization incomplete or rejected. No credentials saved.')
    with httpx.Client(timeout=TIMEOUTS.gateway_http,follow_redirects=False,trust_env=False) as client:
        response = client.post('https://oauth2.googleapis.com/token',data={'code':result['code'],'client_id':client_id,'client_secret':client_secret,'redirect_uri':REDIRECT,'grant_type':'authorization_code','code_verifier':verifier})
        if response.status_code != 200:
            raise SystemExit('Google token exchange failed. No credentials saved.')
        data = response.json()
    jwks = jwt.PyJWKClient('https://www.googleapis.com/oauth2/v3/certs',timeout=TIMEOUTS.gateway_http)
    key = jwks.get_signing_key_from_jwt(data['id_token'])
    claims = jwt.decode(data['id_token'],key.key,algorithms=['RS256'],audience=client_id,options={'require':['exp','iat','sub','iss','aud','nonce','email']})
    if claims['iss'] not in ('accounts.google.com','https://accounts.google.com') or claims.get('email_verified') is not True or not hmac.compare_digest(claims['nonce'],nonce) or claims['email'].lower()!=args.email.lower():
        raise SystemExit('Approved Google account was not verified. No credentials saved.')
    if not data.get('refresh_token') or not set(scopes[2:]).issubset(set(data.get('scope','').split())):
        raise SystemExit('Offline access or required provider scopes missing. No credentials saved.')
    save_credentials(args.env_file,{'GOOGLE_DRIVE_CLIENT_ID':client_id,'GOOGLE_DRIVE_CLIENT_SECRET':client_secret,'GOOGLE_DRIVE_REFRESH_TOKEN':data['refresh_token']})
    print('Google provider refresh credentials saved to the private environment (mode 0600). No secret values displayed.',flush=True)


if __name__=='__main__':
    main()
