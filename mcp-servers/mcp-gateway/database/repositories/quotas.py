"""Atomic shared daily/monthly spending reservations."""
from datetime import timezone
from policy import Denied


class QuotaRepository:
    def __init__(self, database):
        self.database = database

    async def reserve(self, client_id, tool, provider='', credits=0, budget=None):
        if type(credits) is not int or credits < 0:
            raise Denied('Unknown cost')
        if provider and (not budget or any(type(budget.get(k)) is not int or budget[k] <= 0 for k in ('daily', 'monthly'))):
            raise Denied('Paid provider budgets are not approved')
        async with self.database.transaction() as db, db.cursor() as cur:
            # All reservations take the same row lock, then read committed totals.
            # Lock lifetime is exactly this transaction, including pooled clients.
            await cur.execute('SELECT id FROM gateway_quotas.reservation_lock WHERE id = 1 FOR UPDATE')
            if await cur.fetchone() != (1,):
                raise Denied('Gateway quota migration is not ready')
            await cur.execute('SELECT clock_timestamp()')
            now = (await cur.fetchone())[0].astimezone(timezone.utc)
            day, month = now.date(), now.date().replace(day=1)
            if provider:
                for column, value, cap in [('day', day, budget['daily']), ('month', month, budget['monthly'])]:
                    await cur.execute(f'SELECT coalesce(sum(credits),0) FROM gateway_quotas.reservations WHERE provider=%s AND {column}=%s', (provider, value))
                    if (await cur.fetchone())[0] + credits > cap:
                        raise Denied('Shared provider budget exhausted')
            await cur.execute('INSERT INTO gateway_quotas.reservations (client_id,tool,provider,credits,day,month,created) VALUES (%s,%s,%s,%s,%s,%s,%s)', (client_id, tool, provider, credits, day, month, now))
