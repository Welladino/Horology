"""Expiring OAuth records; opaque credentials are indexed only by SHA-256."""
import hashlib
import json
from contextlib import contextmanager


class RecordStore:
    def __init__(self, ledger):
        self.ledger = ledger

    @staticmethod
    def digest(key):
        return hashlib.sha256(key.encode()).hexdigest()

    def put(self, kind, key, value, expires):
        with self.ledger.connect() as db, db.cursor() as cur:
            cur.execute('DELETE FROM gateway_auth.records WHERE expires <= clock_timestamp()')
            cur.execute('INSERT INTO gateway_auth.records(kind,key_hash,data,expires) VALUES(%s,%s,%s::jsonb,to_timestamp(%s)) ON CONFLICT(kind,key_hash) DO UPDATE SET data=EXCLUDED.data,expires=EXCLUDED.expires', (kind, self.digest(key), json.dumps(value), expires))

    def get(self, kind, key, consume=False):
        with self.ledger.connect() as db, db.cursor() as cur:
            if consume:
                cur.execute('DELETE FROM gateway_auth.records WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp() RETURNING data', (kind, self.digest(key)))
            else:
                cur.execute('SELECT data FROM gateway_auth.records WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp()', (kind, self.digest(key)))
            row = cur.fetchone()
            return row[0] if row else None

    def revoke(self, grant):
        with self.grant_transaction() as records:
            records.revoke(grant)

    @contextmanager
    def grant_transaction(self):
        # Serialize issuance and revocation, including overlapping Cloud Run revisions.
        # The quota ledger has its own unrelated lock.
        with self.ledger.connect() as db, db.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('horology-oauth-grants',0))")
            yield TransactionRecords(cur)


class TransactionRecords:
    def __init__(self, cursor):
        self.cursor = cursor

    def get(self, kind, key, consume=False):
        if consume:
            self.cursor.execute('DELETE FROM gateway_auth.records WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp() RETURNING data', (kind, RecordStore.digest(key)))
        else:
            self.cursor.execute('SELECT data FROM gateway_auth.records WHERE kind=%s AND key_hash=%s AND expires>clock_timestamp()', (kind, RecordStore.digest(key)))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def put(self, kind, key, value, expires):
        self.cursor.execute('INSERT INTO gateway_auth.records(kind,key_hash,data,expires) VALUES(%s,%s,%s::jsonb,to_timestamp(%s))', (kind,RecordStore.digest(key),json.dumps(value),expires))

    def revoke(self, grant):
        self.cursor.execute("DELETE FROM gateway_auth.records WHERE kind IN ('access','refresh') AND data->>'grant_id'=%s", (grant,))
