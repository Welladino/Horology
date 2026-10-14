"""Atomic shared daily/monthly spending reservations."""
from psycopg import AsyncClientCursor

from policy import Denied


class QuotaRepository:
    def __init__(self, database):
        self.database = database

    async def reserve(self, client_id, tool, provider='', credits=0, budget=None):
        if type(credits) is not int or credits < 0:
            raise Denied('Unknown cost')
        if provider and (not budget or any(type(budget.get(k)) is not int or budget[k] <= 0 for k in ('daily', 'monthly'))):
            raise Denied('Paid provider budgets are not approved')
        # Two statements, one round trip: they go together as one simple query, which Postgres runs
        # as a single implicit transaction. The first takes the shared lock (waiting for any other
        # reservation to commit); the second starts after it, so its totals include that
        # reservation. One combined statement would read totals from before the wait.
        params = {'client_id': client_id, 'tool': tool, 'provider': provider, 'credits': credits,
                  'daily': budget['daily'] if provider else None, 'monthly': budget['monthly'] if provider else None}
        async with self.database.connection() as db, AsyncClientCursor(db) as cur:
            await cur.execute(
                """
                SELECT id FROM gateway_quotas.reservation_lock WHERE id = 1 FOR UPDATE;
                WITH period AS (
                    SELECT ts, (ts AT TIME ZONE 'UTC')::date AS day, date_trunc('month', ts AT TIME ZONE 'UTC')::date AS month
                    FROM (SELECT clock_timestamp() AS ts) now
                ), used AS (
                    SELECT coalesce(sum(r.credits) FILTER (WHERE r.day = p.day), 0) AS day_used,
                           coalesce(sum(r.credits), 0) AS month_used
                    FROM period p LEFT JOIN gateway_quotas.reservations r
                      ON %(provider)s <> '' AND r.provider = %(provider)s AND r.month = p.month
                ), added AS (
                    INSERT INTO gateway_quotas.reservations (client_id, tool, provider, credits, day, month, created)
                    SELECT %(client_id)s, %(tool)s, %(provider)s, %(credits)s, p.day, p.month, p.ts FROM period p, used u
                    WHERE EXISTS (SELECT 1 FROM gateway_quotas.reservation_lock WHERE id = 1)
                      AND (%(provider)s = '' OR (u.day_used + %(credits)s <= %(daily)s
                                                 AND u.month_used + %(credits)s <= %(monthly)s))
                    RETURNING 1
                )
                SELECT count(*) FROM added;
                """, params)
            locked = await cur.fetchone()
            cur.nextset()
            added = (await cur.fetchone())[0]
        if locked != (1,):
            raise Denied('Gateway quota migration is not ready')
        if not added:
            raise Denied('Shared provider budget exhausted')
