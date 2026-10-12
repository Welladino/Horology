"""Operator policy and persistent, atomic quotas; no agent-supplied run identifiers."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


class Denied(ValueError):
    pass


def load_policy(path):
    policy = json.loads(Path(path).read_text())
    if 'auth' in policy['supabase']['schemas']:
        raise Denied('Auth schema is forbidden')
    for assignment, config in policy.get('assignments', {}).items():
        if not assignment or not isinstance(config['expires_at'], int):
            raise Denied('Assignment must have an expiry')
        if not set(config.get('repositories', [])).issubset(policy['repositories']):
            raise Denied('Assignment repository exceeds global scope')
        if not set(config.get('schemas', [])).issubset(policy['supabase']['schemas']):
            raise Denied('Assignment schema exceeds global scope')
        if not set(config.get('drive_files', [])).issubset(policy['drive']['files']):
            raise Denied('Assignment file exceeds global scope')
    return policy


def authorize(policy, assignment, tool):
    config = policy.get('assignments', {}).get(assignment)
    if not config or config['expires_at'] <= datetime.now(timezone.utc).timestamp():
        raise Denied('Unknown or expired assignment')
    if tool not in config.get('tools', []):
        raise Denied('Tool not allowed for this assignment')
    return config



def credential(name):
    value = os.environ.get(name)
    if not value:
        raise Denied(f'{name} is not configured')
    return value
