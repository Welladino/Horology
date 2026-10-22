"""Gateway use of the shared async Postgres pool; schema changes stay in Alembic."""
from horology_runtime.database import Database as SharedDatabase
from horology_runtime.settings import DATABASE
from policy import Denied


class Database(SharedDatabase):
    def __init__(self, dsn):
        if not dsn:
            raise Denied('GATEWAY_DATABASE_URL is not configured')
        super().__init__(dsn, DATABASE.gateway_pool_size)

    async def check_ready(self):
        async with self.transaction() as db, db.cursor() as cur:
            await cur.execute('SELECT client_id FROM gateway_quotas.reservations LIMIT 0')
            await cur.execute('SELECT client_id FROM gateway_quotas.cache LIMIT 0')
            await cur.execute('SELECT user_id, server_id FROM access.user_mcp_access LIMIT 0')  # access tables (20261016_008)
            await cur.execute('SELECT workspace, project FROM access.workspace_pages LIMIT 0')
            await cur.execute('SELECT id FROM gateway_quotas.reservation_lock WHERE id = 1')
            if await cur.fetchone() != (1,):
                raise Denied('Gateway quota migration is not ready')
