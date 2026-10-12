"""Crash-safe write receipts. Pending external writes require reconciliation, never retries."""
import hashlib
import json
import re
from policy import Denied


class WriteStore:
    def __init__(self, ledger):
        self.ledger = ledger

    def previous(self, assignment, operation, key, payload):
        """Inspect a receipt before validation without claiming a new external write."""
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', key):
            raise Denied('A bounded operation key is required')
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.ledger.connect() as db, db.cursor() as cur:
            cur.execute('SELECT payload_hash,status,result FROM gateway_operations.operations WHERE assignment=%s AND operation=%s AND key=%s', (assignment,operation,key))
            row = cur.fetchone()
        if row is None:
            return None
        if row[0] != digest:
            raise Denied('Operation key was already used with different inputs')
        if row[1] != 'complete':
            raise Denied('Write outcome is uncertain; operator reconciliation required')
        return row[2]

    def begin(self, assignment, operation, key, payload):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', key):
            raise Denied('A bounded operation key is required')
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.ledger.connect() as db, db.cursor() as cur:
            cur.execute("INSERT INTO gateway_operations.operations(assignment,operation,key,payload_hash,status) VALUES(%s,%s,%s,%s,'pending') ON CONFLICT DO NOTHING RETURNING key", (assignment,operation,key,digest))
            if cur.fetchone():
                return None
            cur.execute('SELECT payload_hash,status,result FROM gateway_operations.operations WHERE assignment=%s AND operation=%s AND key=%s', (assignment,operation,key))
            row = cur.fetchone()
            if row[0] != digest:
                raise Denied('Operation key was already used with different inputs')
            if row[1] != 'complete':
                raise Denied('Write outcome is uncertain; operator reconciliation required')
            return row[2]

    def finish(self, assignment, operation, key, result):
        with self.ledger.connect() as db, db.cursor() as cur:
            cur.execute("UPDATE gateway_operations.operations SET status='complete',result=%s::jsonb WHERE assignment=%s AND operation=%s AND key=%s AND status='pending'", (json.dumps(result),assignment,operation,key))
            if cur.rowcount != 1:
                raise Denied('Write receipt could not be finalized')

    def draft(self, assignment, file_id):
        with self.ledger.connect() as db, db.cursor() as cur:
            cur.execute("SELECT result FROM gateway_operations.operations WHERE assignment=%s AND operation='drive_create_draft' AND status='complete' AND result->>'id'=%s", (assignment,file_id))
            rows = cur.fetchall()
        if len(rows) != 1:
            raise Denied('File was not created by this assignment')
        return rows[0][0]
