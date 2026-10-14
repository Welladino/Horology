"""Operator policy and persistent, atomic quotas; no agent-supplied run identifiers."""
import json
import os
from pathlib import Path


class Denied(ValueError):
    pass


def load_policy(path):
    policy = json.loads(Path(path).read_text())
    if 'auth' in policy['supabase']['schemas']:
        raise Denied('Auth schema is forbidden')
    config = policy.get('access')
    if not isinstance(config, dict) or not isinstance(config.get('tools'), list):
        raise Denied('Shared access policy is required')
    if any(tool.startswith(('github_', 'drive_')) for tool in config['tools']):
        raise Denied('GitHub and Google document adapters are parked')
    if not set(config.get('schemas', [])).issubset(policy['supabase']['schemas']):
        raise Denied('Access schema exceeds global scope')
    if not set(config.get('alexandria_operations', [])).issubset(policy.get('alexandria', {}).get('operations', [])):
        raise Denied('Access Alexandria scope exceeds global scope')
    # Countries are 'any' (every ISO code) or an explicit list.
    countries, allowed = config.get('alexandria_countries', []), policy.get('alexandria', {}).get('countries', [])
    if allowed != 'any' and (countries == 'any' or not set(countries).issubset(allowed)):
        raise Denied('Access Alexandria scope exceeds global scope')
    return policy


def authorize(policy, tool):
    config = policy['access']
    if tool not in config.get('tools', []):
        raise Denied('Tool is not allowed by shared policy')
    return config



def credential(name):
    value = os.environ.get(name)
    if not value:
        raise Denied(f'{name} is not configured')
    return value
