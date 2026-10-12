"""Postgres quota ledger. Schema changes belong exclusively to Alembic."""
import json
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
from psycopg2.extensions import parse_dsn
import certifi
from horology_runtime.settings import TIMEOUTS
from policy import Denied


class Ledger:
    def __init__(self, dsn):
        if not dsn:
            raise Denied('GATEWAY_DATABASE_URL is not configured')
        self.dsn = dsn

    @contextmanager
    def connect(self):
        # Do not inherit the container's Supabase-specific PGSSLROOTCERT.
        options = {'sslrootcert': certifi.where()}
        host = parse_dsn(self.dsn).get('host', '')
        if host.endswith('.neon.tech'):
            options['sslmode'] = 'verify-full'
        db = psycopg2.connect(self.dsn, connect_timeout=TIMEOUTS.database_connect, **options)
        try:
            # SET LOCAL is compatible with transaction-mode connection pooling.
            with db:
                with db.cursor() as cur:
                    cur.execute('SET LOCAL statement_timeout = %s', (TIMEOUTS.neon_statement_ms,))
                    cur.execute('SET LOCAL lock_timeout = %s', (TIMEOUTS.neon_lock_ms,))
                yield db
        finally:
            db.close()

    def check_ready(self):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT id FROM gateway_quotas.reservation_lock WHERE id = 1')
            if cur.fetchone() != (1,):
                raise Denied('Gateway quota migration is not ready')

    def reserve(self, assignment, tool, limit, provider='', credits=0, budget=None):
        if type(limit) is not int or limit <= 0:
            raise Denied('No approved per-assignment limit')
        if type(credits) is not int or credits < 0:
            raise Denied('Unknown cost')
        if provider and (not budget or any(type(budget.get(k)) is not int or budget[k] <= 0 for k in ('daily', 'monthly', 'assignment')) or type(budget.get('calls_per_assignment', 2)) is not int or budget.get('calls_per_assignment', 2) <= 0):
            raise Denied('Paid provider budgets are not approved')
        with self.connect() as db, db.cursor() as cur:
            # All reservations take the same row lock, then read committed totals.
            # Lock lifetime is exactly this transaction, including pooled clients.
            cur.execute('SELECT id FROM gateway_quotas.reservation_lock WHERE id = 1 FOR UPDATE')
            if cur.fetchone() != (1,):
                raise Denied('Gateway quota migration is not ready')
            cur.execute('SELECT clock_timestamp()')
            now = cur.fetchone()[0].astimezone(timezone.utc)
            day, month = now.date(), now.date().replace(day=1)
            cur.execute('SELECT count(*) FROM gateway_quotas.reservations WHERE assignment=%s AND tool=%s', (assignment, tool))
            if cur.fetchone()[0] >= limit:
                raise Denied('Assignment tool limit exhausted')
            if provider:
                cur.execute('SELECT count(*) FROM gateway_quotas.reservations WHERE provider=%s AND assignment=%s', (provider, assignment))
                if cur.fetchone()[0] >= budget.get('calls_per_assignment', 2):
                    raise Denied('Paid provider session call limit exhausted')
                for column, value, cap in [('day', day, budget['daily']), ('month', month, budget['monthly']), ('assignment', assignment, budget['assignment'])]:
                    cur.execute(f'SELECT coalesce(sum(credits),0) FROM gateway_quotas.reservations WHERE provider=%s AND {column}=%s', (provider, value))
                    if cur.fetchone()[0] + credits > cap:
                        raise Denied('Shared provider budget exhausted')
            cur.execute('INSERT INTO gateway_quotas.reservations (assignment,tool,provider,credits,day,month,created) VALUES (%s,%s,%s,%s,%s,%s,%s)', (assignment, tool, provider, credits, day, month, now))

    def cached(self, assignment, key):
        with self.connect() as db, db.cursor() as cur:
            cur.execute('SELECT value FROM gateway_quotas.cache WHERE assignment=%s AND key=%s AND expires > clock_timestamp()', (assignment, key))
            row = cur.fetchone()
        return row[0] if row else None

    def save_cache(self, assignment, key, value):
        with self.connect() as db, db.cursor() as cur:
            cur.execute("INSERT INTO gateway_quotas.cache (assignment,key,value,expires) VALUES (%s,%s,%s::jsonb,clock_timestamp()+interval '1 hour') ON CONFLICT (assignment,key) DO UPDATE SET value=EXCLUDED.value,expires=EXCLUDED.expires", (assignment, key, json.dumps(value)))
