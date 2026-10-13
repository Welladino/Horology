"""Expiring OAuth records; opaque credentials are indexed only by SHA-256."""
import hashlib
import json
from contextlib import asynccontextmanager


class OAuthRepository:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def digest(key):
        return hashlib.sha256(key.encode()).hexdigest()

    async def put(self, kind, key, value, expires):
        async with self.database.transaction() as db, db.cursor() as cur:
            await cur.execute('DELETE FROM gateway_auth.records WHERE expires <= clock_timestamp()')
            await cur.execute('INSERT INTO gateway_auth.records(kind,key_hash,data,expires) VALUES(%s,%s,%s::jsonb,to_timestamp(%s)) ON CONFLICT(kind,key_hash) DO UPDATE SET data=EXCLUDED.data,expires=EXCLUDED.expires', (kind, self.digest(key), json.dumps(value), expires))

    async def get(self, kind, key, consume=False):
        async with self.database.transaction() as db, db.cursor() as cur:
            if consume:
                await cur.execute('DELETE FROM gateway_auth.records WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp() RETURNING data', (kind, self.digest(key)))
            else:
                await cur.execute('SELECT data FROM gateway_auth.records WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp()', (kind, self.digest(key)))
            row = await cur.fetchone()
            return row[0] if row else None

    async def revoke(self, grant):
        async with self.grant_transaction() as records:
            await records.revoke(grant)

    async def revoke_email(self, email):
        async with self.grant_transaction() as records:
            return await records.revoke_email(email)

    @asynccontextmanager
    async def grant_transaction(self):
        # Serialize issuance and revocation, including overlapping Cloud Run revisions.
        # The quota ledger has its own unrelated lock.
        async with self.database.transaction() as db, db.cursor() as cur:
            await cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('horology-oauth-grants',0))")
            yield TransactionRecords(cur)


class TransactionRecords:
    def __init__(self, cursor):
        self.cursor = cursor

    async def get(self, kind, key, consume=False):
        if consume:
            await self.cursor.execute('DELETE FROM gateway_auth.records WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp() RETURNING data', (kind, OAuthRepository.digest(key)))
        else:
            await self.cursor.execute('SELECT data FROM gateway_auth.records WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp()', (kind, OAuthRepository.digest(key)))
        row = await self.cursor.fetchone()
        return row[0] if row else None

    async def put(self, kind, key, value, expires):
        await self.cursor.execute('INSERT INTO gateway_auth.records(kind,key_hash,data,expires) VALUES(%s,%s,%s::jsonb,to_timestamp(%s))', (kind,OAuthRepository.digest(key),json.dumps(value),expires))

    async def revoke(self, grant):
        await self.cursor.execute("DELETE FROM gateway_auth.records WHERE kind IN ('access','refresh') AND data->>'grant_id'=%s", (grant,))

    async def revoke_email(self, email):
        # Grants issued before emails were stored have no email and are not matched.
        await self.cursor.execute("DELETE FROM gateway_auth.records WHERE kind IN ('access','refresh') AND data->>'email'=%s", (email.lower(),))
        return self.cursor.rowcount
