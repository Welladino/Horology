"""SQL for graph_runs: the per-workspace run claim and the request cooldown.

Each check-then-claim is one round trip of two statements, sent together as one
simple query (a single implicit transaction): the first takes a per-workspace
lock, the second starts after it, so it sees any claim another request has just
committed. Values are quoted client-side by psycopg.
"""
from psycopg import AsyncClientCursor

_LOCK = "SELECT pg_advisory_xact_lock(hashtext('graph_runs:' || %(workspace)s));"
# A claim holds while its job is starting (unconfirmed) or running (confirmed), until it goes stale.
_HELD = """
    held AS (
        SELECT mode, run_token FROM graph_runs
        WHERE workspace = %(workspace)s AND running_since IS NOT NULL
          AND running_since > now() - make_interval(mins => CASE WHEN confirmed THEN %(stale)s ELSE %(start)s END)
        LIMIT 1
    )"""
_FREE = ("UPDATE graph_runs SET running_since = NULL, run_token = NULL, confirmed = false "
         "WHERE workspace = %(workspace)s AND mode = %(mode)s")


class RunRepository:
    def __init__(self, database, stale_minutes, start_minutes):
        self.database = database
        self.windows = {"stale": stale_minutes, "start": start_minutes}

    async def _locked(self, sql, params, reply=True):
        """Run sql after the workspace lock, in one round trip; returns its (one statement's) row."""
        async with self.database.connection() as conn, AsyncClientCursor(conn) as cur:
            await cur.execute(_LOCK + sql, {**self.windows, **params})
            if reply:
                cur.nextset()
                return await cur.fetchone()

    async def request(self, workspace, mode, cooldown_seconds, token):
        """Take the claim for an agent's request, or return why not: ('running', mode) or ('cooldown', seconds left)."""
        held, wait, taken = await self._locked(
            f"""
            WITH {_HELD}, wait AS (
                SELECT ceil(extract(epoch FROM requested_at + make_interval(secs => %(cooldown)s) - now()))::int AS seconds
                FROM graph_runs WHERE workspace = %(workspace)s AND mode = %(mode)s
                  AND requested_at > now() - make_interval(secs => %(cooldown)s)
            ), taken AS (
                INSERT INTO graph_runs (workspace, mode, running_since, run_token, confirmed, chain, requested_at)
                SELECT %(workspace)s, %(mode)s, now(), %(token)s, false, 1, now()
                WHERE NOT EXISTS (SELECT 1 FROM held) AND NOT EXISTS (SELECT 1 FROM wait)
                ON CONFLICT (workspace, mode) DO UPDATE SET running_since = now(), run_token = EXCLUDED.run_token,
                    confirmed = false, chain = 1, requested_at = now()
                RETURNING 1
            )
            SELECT (SELECT mode FROM held), (SELECT seconds FROM wait), (SELECT count(*) FROM taken);
            """,
            {"workspace": workspace, "mode": mode, "cooldown": cooldown_seconds, "token": token})
        if held:
            return ("running", held)
        if not taken:
            return ("cooldown", max(1, wait or 1))
        return None

    async def cancel_request(self, workspace, mode):
        """The job didn't start: free the claim and forget the request, so the agent can ask again."""
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute("UPDATE graph_runs SET running_since = NULL, run_token = NULL, confirmed = false, "
                              "requested_at = NULL WHERE workspace = %s AND mode = %s", (workspace, mode))

    async def claim(self, workspace, mode, chain, token):
        """Confirm the claim made for this run (same mode and token), or take a free workspace.
        Returns the mode holding the workspace instead, if it isn't ours."""
        held, taken = await self._locked(
            f"""
            WITH {_HELD}, taken AS (
                INSERT INTO graph_runs (workspace, mode, running_since, run_token, confirmed, chain)
                SELECT %(workspace)s, %(mode)s, now(), %(token)s, true, %(chain)s
                WHERE NOT EXISTS (SELECT 1 FROM held
                                  WHERE NOT (%(token)s::text IS NOT NULL AND mode = %(mode)s AND run_token = %(token)s))
                ON CONFLICT (workspace, mode) DO UPDATE SET running_since = now(), run_token = EXCLUDED.run_token,
                    confirmed = true, chain = EXCLUDED.chain
                RETURNING 1
            )
            SELECT (SELECT mode FROM held), (SELECT count(*) FROM taken);
            """,
            {"workspace": workspace, "mode": mode, "chain": chain, "token": token})
        return None if taken else held

    async def release(self, workspace, mode):
        async with self.database.connection() as conn, AsyncClientCursor(conn) as cur:
            await cur.execute(_FREE, {"workspace": workspace, "mode": mode})

    async def hand_over(self, workspace, from_mode, to_mode, chain, token):
        """Pass the claim from this run to its follow-up in one step: nothing can start in between."""
        await self._locked(
            _FREE.replace("%(mode)s", "%(from_mode)s") + """;
            INSERT INTO graph_runs (workspace, mode, running_since, run_token, confirmed, chain)
            VALUES (%(workspace)s, %(to_mode)s, now(), %(token)s, false, %(chain)s)
            ON CONFLICT (workspace, mode) DO UPDATE SET running_since = now(), run_token = EXCLUDED.run_token,
                confirmed = false, chain = EXCLUDED.chain;
            """,
            {"workspace": workspace, "from_mode": from_mode, "to_mode": to_mode, "chain": chain, "token": token},
            reply=False)
