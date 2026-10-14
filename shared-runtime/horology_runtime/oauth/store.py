"""Expiring OAuth records in one service's own table; opaque credentials are indexed only by SHA-256."""
import hashlib
import json
from contextlib import asynccontextmanager


TABLES = ('gateway_auth.records', 'graph_auth.records')


class OAuthRepository:
    def __init__(self, database, table):
        # Each service keeps its own table, so one service's tokens are never
        # found by another. Only known table names are accepted.
        if table not in TABLES:
            raise ValueError('Unknown OAuth records table')
        self.database, self.table = database, table

    @staticmethod
    def digest(key):
        return hashlib.sha256(key.encode()).hexdigest()

    async def put(self, kind, key, value, expires):
        # One statement: expired records go in the same round trip as the write. The record being
        # written is left out of the clean-up, so the statement never touches one row twice.
        digest = self.digest(key)
        async with self.database.connection() as db, db.cursor() as cur:
            await cur.execute(f'WITH expired AS (DELETE FROM {self.table} WHERE expires <= clock_timestamp() '  # nosec B608: table name from the fixed TABLES list; values are bound parameters
                              f'AND NOT (kind = %s AND key_hash = %s)) '
                              f'INSERT INTO {self.table}(kind,key_hash,data,expires) VALUES(%s,%s,%s::jsonb,to_timestamp(%s)) ON CONFLICT(kind,key_hash) DO UPDATE SET data=EXCLUDED.data,expires=EXCLUDED.expires', (kind, digest, kind, digest, json.dumps(value), expires))

    async def get(self, kind, key, consume=False):
        async with self.database.connection() as db, db.cursor() as cur:
            return await TransactionRecords(cur, self.table).get(kind, key, consume)

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
            await cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ('horology-oauth-grants:'+self.table,))
            yield TransactionRecords(cur, self.table)


class TransactionRecords:
    def __init__(self, cursor, table):
        self.cursor, self.table = cursor, table

    async def get(self, kind, key, consume=False):
        if consume:
            await self.cursor.execute(f'DELETE FROM {self.table} WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp() RETURNING data', (kind, OAuthRepository.digest(key)))  # nosec B608: table name from the fixed TABLES list; values are bound parameters
        else:
            await self.cursor.execute(f'SELECT data FROM {self.table} WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp()', (kind, OAuthRepository.digest(key)))  # nosec B608: table name from the fixed TABLES list; values are bound parameters
        row = await self.cursor.fetchone()
        return row[0] if row else None

    async def put(self, kind, key, value, expires):
        await self.cursor.execute(f'INSERT INTO {self.table}(kind,key_hash,data,expires) VALUES(%s,%s,%s::jsonb,to_timestamp(%s))', (kind,OAuthRepository.digest(key),json.dumps(value),expires))  # nosec B608: table name from the fixed TABLES list; values are bound parameters

    async def revoke(self, grant):
        await self.cursor.execute(f"DELETE FROM {self.table} WHERE kind IN ('access','refresh') AND data->>'grant_id'=%s", (grant,))  # nosec B608: table name from the fixed TABLES list; values are bound parameters

    async def revoke_email(self, email):
        # Grants issued before emails were stored have no email and are not matched.
        await self.cursor.execute(f"DELETE FROM {self.table} WHERE kind IN ('access','refresh') AND data->>'email'=%s", (email.lower(),))  # nosec B608: table name from the fixed TABLES list; values are bound parameters
        return self.cursor.rowcount
