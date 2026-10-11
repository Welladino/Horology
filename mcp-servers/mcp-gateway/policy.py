"""Operator policy and persistent, atomic quotas; no agent-supplied run identifiers."""
import json
import os
import sqlite3
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


class Ledger:
    """SQLite is suitable only for one local gateway deployment, with persistent disk.

    Reservations are retained on upstream failure/timeout; there are no automatic
    retries or refunds. Multiple connections serialize through BEGIN IMMEDIATE.
    """
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS reservations (assignment TEXT, tool TEXT, provider TEXT, credits INTEGER, day TEXT, month TEXT, created TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS cache (assignment TEXT, key TEXT, value TEXT, expires INTEGER, PRIMARY KEY(assignment,key))')

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def reserve(self, assignment, tool, limit, provider='', credits=0, budget=None):
        if type(limit) is not int or limit <= 0:
            raise Denied('No approved per-assignment limit')
        if type(credits) is not int or credits < 0:
            raise Denied('Unknown cost')
        now = datetime.now(timezone.utc)
        day, month = now.strftime('%Y-%m-%d'), now.strftime('%Y-%m')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            count = db.execute('SELECT count(*) FROM reservations WHERE assignment=? AND tool=?', (assignment, tool)).fetchone()[0]
            if count >= limit:
                raise Denied('Assignment tool limit exhausted')
            if provider:
                if not budget or any(type(budget.get(k)) is not int or budget[k] <= 0 for k in ('daily', 'monthly', 'assignment')):
                    raise Denied('Paid provider budgets are not approved')
                provider_calls = db.execute('SELECT count(*) FROM reservations WHERE provider=? AND assignment=?', (provider, assignment)).fetchone()[0]
                if provider_calls >= budget.get('calls_per_assignment', 2):
                    raise Denied('Paid provider session call limit exhausted')
                for column, value, cap in [('day', day, budget['daily']), ('month', month, budget['monthly']), ('assignment', assignment, budget['assignment'])]:
                    used = db.execute(f'SELECT coalesce(sum(credits),0) FROM reservations WHERE provider=? AND {column}=?', (provider, value)).fetchone()[0]
                    if used + credits > cap:
                        raise Denied('Shared provider budget exhausted')
            db.execute('INSERT INTO reservations VALUES (?,?,?,?,?,?,?)', (assignment, tool, provider, credits, day, month, now.isoformat()))

    def cached(self, assignment, key):
        with self.connect() as db:
            row = db.execute('SELECT value,expires FROM cache WHERE assignment=? AND key=?', (assignment, key)).fetchone()
        if row and row[1] > datetime.now(timezone.utc).timestamp():
            return json.loads(row[0])

    def save_cache(self, assignment, key, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?,?)', (assignment, key, json.dumps(value), int(datetime.now(timezone.utc).timestamp()) + 3600))


def credential(name):
    value = os.environ.get(name)
    if not value:
        raise Denied(f'{name} is not configured')
    return value
