"""SQL for graph_runs: the per-workspace run claim and the request cooldown."""

# Taken inside each transaction below, so two requests or runs for one workspace
# can't both pass the checks at the same moment.
_LOCK = "SELECT pg_advisory_xact_lock(hashtext('graph_runs:' || %s))"
# A claim holds while its job is starting (unconfirmed) or running (confirmed), until it goes stale.
_HELD = """
    SELECT mode, run_token FROM graph_runs
    WHERE workspace = %s AND running_since IS NOT NULL
      AND running_since > now() - make_interval(mins => CASE WHEN confirmed THEN %s ELSE %s END)
    LIMIT 1
"""
_TAKE = """
    INSERT INTO graph_runs (workspace, mode, running_since, run_token, confirmed, chain)
    VALUES (%s, %s, now(), %s, %s, %s)
    ON CONFLICT (workspace, mode) DO UPDATE SET running_since = now(), run_token = EXCLUDED.run_token,
        confirmed = EXCLUDED.confirmed, chain = EXCLUDED.chain
"""
_FREE = "UPDATE graph_runs SET running_since = NULL, run_token = NULL, confirmed = false WHERE workspace = %s AND mode = %s"


class RunRepository:
    def __init__(self, database, stale_minutes, start_minutes):
        self.database = database
        self.windows = (stale_minutes, start_minutes)

    async def _held(self, cur, workspace):
        await cur.execute(_HELD, (workspace, *self.windows))
        return await cur.fetchone()

    async def request(self, workspace, mode, cooldown_seconds, token):
        """Take the claim for an agent's request, or return why not: ('running', mode) or ('cooldown', seconds left)."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(_LOCK, (workspace,))
            held = await self._held(cur, workspace)
            if held:
                return ("running", held[0])
            await cur.execute(
                """
                SELECT ceil(extract(epoch FROM requested_at + make_interval(secs => %s) - now()))::int
                FROM graph_runs WHERE workspace = %s AND mode = %s
                  AND requested_at > now() - make_interval(secs => %s)
                """,
                (cooldown_seconds, workspace, mode, cooldown_seconds))
            waiting = await cur.fetchone()
            if waiting:
                return ("cooldown", max(1, waiting[0]))
            await cur.execute(_TAKE, (workspace, mode, token, False, 1))
            await cur.execute("UPDATE graph_runs SET requested_at = now() WHERE workspace = %s AND mode = %s",
                              (workspace, mode))
            return None

    async def cancel_request(self, workspace, mode):
        """The job didn't start: free the claim and forget the request, so the agent can ask again."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(_FREE, (workspace, mode))
            await cur.execute("UPDATE graph_runs SET requested_at = NULL WHERE workspace = %s AND mode = %s",
                              (workspace, mode))

    async def claim(self, workspace, mode, chain, token):
        """Confirm the claim made for this run (same mode and token), or take a free workspace.
        Returns the mode holding the workspace instead, if it isn't ours."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(_LOCK, (workspace,))
            held = await self._held(cur, workspace)
            if held and not (token and held == (mode, token)):
                return held[0]
            await cur.execute(_TAKE, (workspace, mode, token, True, chain))
            return None

    async def release(self, workspace, mode):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(_FREE, (workspace, mode))

    async def hand_over(self, workspace, from_mode, to_mode, chain, token):
        """Pass the claim from this run to its follow-up in one step: nothing can start in between."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(_LOCK, (workspace,))
            await cur.execute(_FREE, (workspace, from_mode))
            await cur.execute(_TAKE, (workspace, to_mode, token, False, chain))
