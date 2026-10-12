"""Client-scoped one-hour JSON response cache."""
import json


class CacheRepository:
    def __init__(self, database):
        self.database = database

    async def cached(self, client_id, key):
        async with self.database.transaction() as db, db.cursor() as cur:
            await cur.execute('SELECT value FROM gateway_quotas.cache WHERE client_id=%s AND key=%s AND expires > clock_timestamp()', (client_id, key))
            row = await cur.fetchone()
        return row[0] if row else None

    async def save_cache(self, client_id, key, value):
        async with self.database.transaction() as db, db.cursor() as cur:
            await cur.execute("INSERT INTO gateway_quotas.cache (client_id,key,value,expires) VALUES (%s,%s,%s::jsonb,clock_timestamp()+interval '1 hour') ON CONFLICT (client_id,key) DO UPDATE SET value=EXCLUDED.value,expires=EXCLUDED.expires", (client_id, key, json.dumps(value)))
