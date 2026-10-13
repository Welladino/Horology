"""MCP OAuth client grants for one service; Google establishes identity only.

The service supplies its scope, an account check and its consent wording.
Tokens are bound to that service's /mcp resource and stored in its own table.
"""
import asyncio
import hashlib
import hmac
import secrets
import re
import time
from collections import OrderedDict
from urllib.parse import urlencode, urlparse

import httpx
import jwt
from mcp.server.auth.provider import AccessToken, AuthorizationCode, AuthorizationParams, RefreshToken, TokenError, RegistrationError, AuthorizeError
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.responses import RedirectResponse, HTMLResponse
from horology_runtime.settings import TIMEOUTS, OAUTH
from .consent_page import render_consent


class GatewayCode(AuthorizationCode):
    grant_id: str
    email: str = ''


class GatewayRefresh(RefreshToken):
    grant_id: str
    resource: str
    email: str = ''


class GoogleOAuthProvider:
    def __init__(self, store, public_url, client_id, client_secret, *, scope, consent, check=lambda email: None, legacy=None):
        """consent() returns (sections, tool names, note) for the consent page.
        check(email) raises when the signed-in account may not use this service
        right now; it runs at sign-in and on every token load and refresh."""
        # Who may sign in is managed by Google Auth Platform Audience test users.
        if not client_id or not client_secret:
            raise ValueError('Google OAuth credentials are required')
        self.store, self.url, self.scope = store, public_url, scope
        self.client_id, self.client_secret = client_id, client_secret
        self.consent_info, self.check = consent, check
        self.legacy = legacy
        # sha256(token) -> (remember_until, record); least recently used dropped first.
        self.verified = OrderedDict()
        self.jwks = jwt.PyJWKClient('https://www.googleapis.com/oauth2/v3/certs', timeout=TIMEOUTS.gateway_http)

    async def get_client(self, client_id):
        data = await self.store.get('client', client_id)
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def register_client(self, client_info):
        for uri in client_info.redirect_uris or []:
            parsed = urlparse(str(uri))
            if parsed.username or parsed.password or parsed.fragment or not parsed.hostname or not re.fullmatch(r'[A-Za-z0-9.:\[\]-]+', parsed.netloc) or not (parsed.scheme == 'https' or parsed.scheme == 'http' and parsed.hostname in ('localhost','127.0.0.1','::1')):
                raise RegistrationError(error='invalid_redirect_uri', error_description='HTTPS or loopback redirect required')
        if len(client_info.model_dump_json()) > 16384:
            raise RegistrationError(error='invalid_client_metadata', error_description='Client metadata too large')
        await self.store.put('client', client_info.client_id, client_info.model_dump(mode='json'), time.time()+OAUTH.client_seconds)

    async def authorize(self, client, params):
        if params.resource and params.resource != self.url+'/mcp':
            raise AuthorizeError(error='invalid_target', error_description='Unknown resource')
        if params.scopes and set(params.scopes) != {self.scope}:
            raise AuthorizeError(error='invalid_scope', error_description=f'Only {self.scope} scope is supported')
        state = secrets.token_urlsafe(32)
        await self.store.put('login', state, {'params': params.model_dump(mode='json'), 'client_id': client.client_id, 'nonce': secrets.token_urlsafe(32)}, time.time()+OAUTH.login_seconds)
        return self.url+'/auth/google/start?'+urlencode({'state':state})

    def cookie(self, response, value):
        response.set_cookie('horology_oauth', value, max_age=OAUTH.login_seconds, path='/auth', secure=self.url.startswith('https:'), httponly=True, samesite='lax')
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    async def start(self, request):
        state = request.query_params.get('state','')
        data = await self.store.get('login', state)
        if not data:
            return HTMLResponse('Login expired. Start again from your MCP client.', status_code=400)
        response = RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':self.client_id,'redirect_uri':self.url+'/auth/google/callback','response_type':'code','scope':'openid email','state':state,'nonce':data['nonce'],'prompt':'select_account'}))
        return self.cookie(response, state)

    async def verify_google(self, code, nonce):
        async with httpx.AsyncClient(timeout=TIMEOUTS.gateway_http, follow_redirects=False, trust_env=False) as client:
            response = await client.post('https://oauth2.googleapis.com/token', data={'code':code,'client_id':self.client_id,'client_secret':self.client_secret,'redirect_uri':self.url+'/auth/google/callback','grant_type':'authorization_code'})
            response.raise_for_status()
            encoded = response.json()['id_token']
        key = await asyncio.to_thread(self.jwks.get_signing_key_from_jwt, encoded)
        claims = jwt.decode(encoded, key.key, algorithms=['RS256'], audience=self.client_id, options={'require':['exp','iat','sub','iss','aud','nonce','email']})
        if claims['iss'] not in ('https://accounts.google.com','accounts.google.com') or claims.get('email_verified') is not True or not hmac.compare_digest(claims['nonce'], nonce):
            raise ValueError('Invalid Google identity')
        return claims

    async def callback(self, request):
        state = request.query_params.get('state','')
        if not state or not hmac.compare_digest(state, request.cookies.get('horology_oauth','')):
            return HTMLResponse('Login rejected. Start again from your MCP client.', status_code=400)
        data = await self.store.get('login', state, consume=True)
        if not data:
            return HTMLResponse('Login expired. Start again.', status_code=400)
        try:
            claims = await self.verify_google(request.query_params.get('code',''), data['nonce'])
            self.check(claims['email'].lower())
            sections, tools, note = self.consent_info()
            client = await self.get_client(data['client_id'])
            if client is None:
                raise ValueError('Client expired')
        except Exception:
            return HTMLResponse('Sign-in could not be authorized. Check the account is an approved test user.', status_code=403)
        consent = secrets.token_urlsafe(32)
        # Stored in plain text on the grant so scripts/revoke_email.py can find it.
        data.update(subject=claims['sub'], email=claims['email'].lower())
        await self.store.put('consent', consent, data, time.time()+OAUTH.login_seconds)
        # Chrome applies form-action to the POST's final redirect too. Permit
        # only this SDK-validated client callback origin, including its port.
        redirect = urlparse(data['params']['redirect_uri'])
        callback_origin = f'{redirect.scheme}://{redirect.netloc}'
        body, csp = render_consent(client.client_name or client.client_id, claims["email"], consent, sections, tools, callback_origin, note)
        response = HTMLResponse(body, headers={"Content-Security-Policy": csp, "X-Content-Type-Options": "nosniff"})
        return self.cookie(response, consent)

    async def consent(self, request):
        form = await request.form()
        secret = str(form.get('consent',''))
        if not secret or not hmac.compare_digest(secret, request.cookies.get('horology_oauth','')):
            return HTMLResponse('Consent rejected.', status_code=400)
        data = await self.store.get('consent', secret, consume=True)
        if not data:
            return HTMLResponse('Consent expired.', status_code=400)
        params = AuthorizationParams.model_validate(data['params'])
        query = {'state':params.state} if params.state is not None else {}
        if form.get('decision') != 'allow':
            query['error'] = 'access_denied'
        else:
            try:
                self.check(data.get('email', ''))
            except Exception:
                return HTMLResponse('Sign-in could not be authorized. Check the account is an approved test user.', status_code=403)
            code = secrets.token_urlsafe(32)
            model = GatewayCode(code=code, scopes=[self.scope], expires_at=time.time()+OAUTH.code_seconds, client_id=data['client_id'], code_challenge=params.code_challenge, redirect_uri=params.redirect_uri, redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly, resource=self.url+'/mcp', subject=data['subject'], email=data.get('email', ''), grant_id=secrets.token_urlsafe(32))
            await self.store.put('code', code, model.model_dump(mode='json',exclude={'code'}), model.expires_at)
            query['code'] = code
        target = str(params.redirect_uri)
        response = RedirectResponse(target+('&' if '?' in target else '?')+urlencode(query), status_code=303)
        response.delete_cookie('horology_oauth',path='/auth')
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    async def load_authorization_code(self, client, authorization_code):
        data = await self.store.get('code', authorization_code)
        return GatewayCode(code=authorization_code, **data) if data else None

    async def load_refresh_token(self, client, refresh_token):
        data = await self.store.get('refresh', refresh_token)
        return GatewayRefresh(token=refresh_token, **data) if data else None

    async def issue(self, grant, scopes, records):
        self.check(grant.email)
        now = int(time.time())
        access_expiry = now+OAUTH.access_seconds
        refresh_expiry = now+OAUTH.refresh_seconds
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        common = {'client_id':grant.client_id,'subject':grant.subject,'email':grant.email,'scopes':scopes,'resource':self.url+'/mcp'}
        await records.put('access',access,{**common,'expires_at':access_expiry,'claims':{'grant_id':grant.grant_id,'email':grant.email},'grant_id':grant.grant_id},access_expiry)
        await records.put('refresh',refresh,{**common,'expires_at':refresh_expiry,'grant_id':grant.grant_id},refresh_expiry)
        return OAuthToken(access_token=access,token_type='Bearer',expires_in=access_expiry-now,refresh_token=refresh,scope=' '.join(scopes))

    async def exchange_authorization_code(self, client, authorization_code):
        try:
            async with self.store.grant_transaction() as records:
                data = await records.get('code', authorization_code.code, consume=True)
                if not data or data['client_id'] != client.client_id:
                    raise ValueError('Code unavailable')
                result = await self.issue(GatewayCode(code=authorization_code.code,**data), [self.scope], records)
        except ValueError:
            # SDK errors are frozen dataclasses: raise outside generator contexts.
            raise TokenError(error='invalid_grant',error_description='Authorization code unavailable') from None
        return result

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        try:
            async with self.store.grant_transaction() as records:
                data = await records.get('refresh', refresh_token.token, consume=True)
                if not data or data['client_id'] != client.client_id or not set(scopes).issubset({self.scope}):
                    raise ValueError('Refresh unavailable')
                result = await self.issue(GatewayRefresh(token=refresh_token.token,**data),scopes, records)
        except ValueError:
            raise TokenError(error='invalid_grant',error_description='Refresh token unavailable') from None
        return result

    async def load_access_token(self, token):
        key = hashlib.sha256(token.encode()).hexdigest()
        now = time.time()
        cached = self.verified.pop(key, None)
        if cached and cached[0] > now:
            data = dict(cached[1])
        else:
            data = await self.store.get('access',token)
            if not data:
                return await self.legacy.verify_token(token) if self.legacy else None
            # A token issued for another service's resource is never accepted here.
            if data.get('resource') != self.url+'/mcp':
                return None
            cached = (min(now+OAUTH.access_cache_seconds, data['expires_at']), dict(data))
        # The account check runs on every call, cached or not.
        try:
            self.check(data.get('email', ''))
        except Exception:
            return None
        self.verified[key] = cached
        while len(self.verified) > OAUTH.access_cache_size:
            self.verified.popitem(last=False)
        data.pop('grant_id',None)
        return AccessToken(token=token,**data)

    async def revoke_token(self, token):
        grant = token.grant_id if isinstance(token,GatewayRefresh) else (token.claims or {}).get('grant_id')
        if grant:
            await self.store.revoke(grant)
            for key in [k for k, (_, record) in self.verified.items() if record.get('grant_id') == grant]:
                del self.verified[key]

    async def exchange_identity_assertion(self, client, params):
        raise TokenError(error='unsupported_grant_type',error_description='Identity assertion grants are disabled')
