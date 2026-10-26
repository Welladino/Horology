"""Who may use which MCP server and workspace, read from Neon and cached.

Each MCP server builds one Directory with its own server id (the row in
mcp_servers). check() runs on every request through the OAuth provider, so
lookups are cached per email: an LRU of ACCESS.cache_size entries, each kept
ACCESS.cache_seconds (misses ACCESS.miss_seconds). A change made with
scripts/ops/mcp/access.py reaches every instance within that time.
"""
import time
from collections import OrderedDict
from dataclasses import dataclass

from .settings import ACCESS


class AccessDenied(PermissionError):
    """The account may not use this server or workspace."""


@dataclass(frozen=True)
class Account:
    user_id: int
    active: bool
    servers: frozenset  # active servers granted to this user
    workspaces: tuple  # active workspaces this user belongs to, sorted


_LOOKUP = """
    SELECT u.id, u.active,
           coalesce((SELECT array_agg(a.server_id) FROM access.user_mcp_access a
                     JOIN access.mcp_servers s ON s.id = a.server_id AND s.active
                     WHERE a.user_id = u.id), '{}'),
           coalesce((SELECT array_agg(m.workspace ORDER BY m.workspace) FROM access.workspace_members m
                     JOIN access.workspaces w ON w.name = m.workspace AND w.active
                     WHERE m.user_id = u.id), '{}')
    FROM access.users u WHERE u.email = %s
"""


class Directory:
    def __init__(self, database, server, *, ttl=ACCESS.cache_seconds, miss_ttl=ACCESS.miss_seconds,
                 size=ACCESS.cache_size, clock=time.monotonic):
        self.database, self.server = database, server
        self.ttl, self.miss_ttl, self.size, self.clock = ttl, miss_ttl, size, clock
        self._cache = OrderedDict()  # email -> (expires, Account or None), least recently used first

    async def _fetch(self, email):
        async with self.database.connection() as db, db.cursor() as cur:
            await cur.execute(_LOOKUP, (email,))
            row = await cur.fetchone()
        return Account(row[0], row[1], frozenset(row[2]), tuple(row[3])) if row else None

    async def account(self, email):
        email = (email or '').strip().lower()
        if not email:
            return None
        now = self.clock()
        cached = self._cache.pop(email, None)
        if cached and cached[0] > now:
            account = cached[1]
        else:
            account = await self._fetch(email)
        self._cache[email] = (cached[0] if cached and cached[0] > now
                              else now + (self.ttl if account else self.miss_ttl), account)
        while len(self._cache) > self.size:
            self._cache.popitem(last=False)
        return account

    async def _allowed(self, email):
        account = await self.account(email)
        if account is None or not account.active or self.server not in account.servers:
            raise AccessDenied('This account may not use this server')
        return account

    async def check(self, email, workspace=None):
        """Raise AccessDenied unless the account may use this server, and (when
        workspace is given) that workspace. Returns the workspace to use: the
        given one, or the only one for a token issued without a workspace."""
        account = await self._allowed(email)
        if workspace is None:
            return None
        if workspace == '':
            if len(account.workspaces) == 1:
                return account.workspaces[0]
            raise AccessDenied('Choose a workspace: reconnect to sign in again')
        if workspace not in account.workspaces:
            raise AccessDenied('This account is not a member of that workspace')
        return workspace

    async def workspaces(self, email):
        """The active workspaces this account may open on this server (empty if none)."""
        return list((await self._allowed(email)).workspaces)

    def forget(self, email=None):
        """Drop cached entries (one email, or all), e.g. in tests or after an admin change."""
        if email is None:
            self._cache.clear()
        else:
            self._cache.pop(email.strip().lower(), None)
