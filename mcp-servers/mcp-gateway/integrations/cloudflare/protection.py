"""Fail closed unless Pages and both Access hostnames are privately scoped."""
import os

import httpx

from .client import ACCOUNT_ID, API, PROJECT_NAME, _result


class ProtectionNotReady(Exception):
    """The administrator must configure or repair workspace publishing."""


def _exact_emails(policies):
    allowed = set()
    if not policies:
        raise ProtectionNotReady()
    for policy in policies:
        if policy.get('decision') != 'allow' or not policy.get('include'):
            raise ProtectionNotReady()
        for rule in policy['include']:
            selector = rule.get('email') if isinstance(rule, dict) else None
            email = selector.get('email') if isinstance(selector, dict) else None
            if not isinstance(email, str) or '@' not in email:
                # Broad domains, everyone, bypass and unknown rules are not safe.
                raise ProtectionNotReady()
            allowed.add(email.lower())
    return allowed


async def _app(client, path, app_id, domain, members, caller, headers):
    app = _result(await client.get(f'{path}/access/apps/{app_id}', headers=headers))
    if not isinstance(app, dict) or app.get('type') != 'self_hosted' or app.get('domain') != domain:
        raise ProtectionNotReady()
    destinations = app.get('destinations')
    if destinations is not None and (not isinstance(destinations, list) or not destinations
                                     or any(not isinstance(item, dict) or item.get('uri') != domain
                                            or item.get('overrides') for item in destinations)):
        raise ProtectionNotReady()
    policies = _result(await client.get(f'{path}/access/apps/{app_id}/policies', headers=headers))
    if not isinstance(policies, list) or not policies:
        raise ProtectionNotReady()
    resolved = []
    for policy in policies:
        if not isinstance(policy, dict) or not policy.get('id'):
            raise ProtectionNotReady()
        if 'include' not in policy:
            response = await client.get(f'{path}/access/apps/{app_id}/policies/{policy["id"]}', headers=headers)
            if response.status_code == 404:
                response = await client.get(f'{path}/access/policies/{policy["id"]}', headers=headers)
            policy = _result(response)
        if not isinstance(policy, dict):
            raise ProtectionNotReady()
        resolved.append(policy)
    emails = _exact_emails(resolved)
    if caller not in emails or not emails.issubset(members):
        raise ProtectionNotReady()


async def ensure_private(config, members, caller):
    """Read live Cloudflare configuration before any upload; no cached assurance."""
    project = config.get('project')
    if (not config.get('enabled') or not isinstance(project, str) or not PROJECT_NAME.fullmatch(project)
            or not config.get('main_app_id') or not config.get('preview_app_id')):
        raise ProtectionNotReady()
    pages_token = os.environ.get('CLOUDFLARE_PAGES_API_TOKEN', '').strip()
    access_token = os.environ.get('CLOUDFLARE_ACCESS_API_TOKEN', '').strip() or pages_token
    if not pages_token:
        raise ProtectionNotReady()
    path = f'/accounts/{ACCOUNT_ID}'
    pages_headers = {'Authorization': f'Bearer {pages_token}'}
    access_headers = {'Authorization': f'Bearer {access_token}'}
    try:
        async with httpx.AsyncClient(base_url=API, timeout=15, trust_env=False, follow_redirects=False) as client:
            page = _result(await client.get(f'{path}/pages/projects/{project}', headers=pages_headers))
            if not isinstance(page, dict) or page.get('name') != project:
                raise ProtectionNotReady()
            await _app(client, path, config['main_app_id'], f'{project}.pages.dev', members, caller, access_headers)
            await _app(client, path, config['preview_app_id'], f'*.{project}.pages.dev', members, caller, access_headers)
    except (httpx.HTTPError, RuntimeError, KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ProtectionNotReady() from exc
