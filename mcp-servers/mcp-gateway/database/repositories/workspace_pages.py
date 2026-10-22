"""Read-only workspace publishing configuration and viewer membership."""


class WorkspacePagesRepository:
    def __init__(self, database):
        self.database = database

    async def get(self, workspace):
        async with self.database.connection() as db, db.cursor() as cur:
            await cur.execute("""
                SELECT p.project, p.main_access_app_id, p.preview_access_app_id, p.enabled
                FROM access.workspace_pages p
                JOIN access.workspaces w ON w.name = p.workspace AND w.active
                WHERE p.workspace = %s
            """, (workspace,))
            row = await cur.fetchone()
        if row is None:
            return None
        return dict(zip(('project', 'main_app_id', 'preview_app_id', 'enabled'), row))

    async def viewers(self, workspace):
        async with self.database.connection() as db, db.cursor() as cur:
            await cur.execute("""
                SELECT u.email FROM access.users u
                JOIN access.workspace_members m ON m.user_id = u.id
                WHERE m.workspace = %s AND u.active
                ORDER BY u.email
            """, (workspace,))
            return {row[0] for row in await cur.fetchall()}
