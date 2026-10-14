"""Run claims, cooldown and follow-ups against a disposable migrated Postgres, as the horology_graph login.
Starting the Cloud Run job is faked; the fake records the token each run is given."""
import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest

import graph_core
from graph_core.runs import cloud_run, service as runs

WS = "runs-test"


@pytest.fixture
def database():
    dsn = os.environ.get("GRAPH_TEST_RUNTIME_URL")
    if not dsn:
        pytest.skip("Disposable migrated Postgres with the horology_graph login is required")
    return dsn


def with_database(dsn, body):
    from horology_runtime.database import Database

    async def run():
        async with Database(dsn, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM graph_runs WHERE workspace = %s", (WS,))
                await body(db)
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM graph_runs WHERE workspace = %s", (WS,))
                graph_core.configure(None)
    asyncio.run(run())


def fake_start():
    """cloud_run.start that records (mode, chain, token) for each run started."""
    started = []

    async def start(workspace, mode, chain, token):
        started.append((mode, chain, token))
        return f"operations/{len(started)}"
    return started, start


async def age(db, minutes, confirmed):
    async with db.transaction() as conn, conn.cursor() as cur:
        await cur.execute("UPDATE graph_runs SET running_since = now() - make_interval(mins => %s) "
                          "WHERE workspace = %s AND confirmed = %s AND running_since IS NOT NULL", (minutes, WS, confirmed))


def test_a_second_request_is_refused_before_the_first_job_starts(database):
    async def body(db):
        started, start = fake_start()
        with patch.object(cloud_run, "start", start):
            assert (await runs.request(WS, "sync"))["started"] is True
            # The job hasn't started yet, but the workspace is already claimed.
            busy = await runs.request(WS, "topics")
            assert busy["reason"] == "already_running" and busy["running"] == "sync"
            assert len(started) == 1

            _, _, token = started[0]
            assert await runs.claim(WS, "topics", 1, None) == "sync"  # a run started by hand waits
            assert await runs.claim(WS, "sync", 1, "someone-else") == "sync"
            assert await runs.claim(WS, "sync", 1, token) is None  # the requested job confirms its claim
            assert (await runs.request(WS, "entities"))["reason"] == "already_running"
            await runs.release(WS, "sync")
            again = await runs.request(WS, "sync")
            assert again["reason"] == "cooldown" and 290 <= again["retry_after_seconds"] <= 300
            assert (await runs.request(WS, "topics"))["started"] is True  # the cooldown is per mode
    with_database(database, body)


def test_claims_expire_if_the_job_never_starts_or_crashes(database):
    async def body(db):
        started, start = fake_start()
        with patch.object(cloud_run, "start", start):
            assert (await runs.request(WS, "sync"))["started"] is True
        await age(db, runs.START_MINUTES + 1, confirmed=False)  # the job never started
        assert await runs.claim(WS, "entities") is None  # a run started by hand can go
        await age(db, 30, confirmed=True)
        assert await runs.claim(WS, "topics") == "entities"  # still running at 30 minutes
        await age(db, runs.STALE_MINUTES + 1, confirmed=True)  # it crashed
        assert await runs.claim(WS, "topics") is None
    with_database(database, body)


def test_a_finished_run_hands_its_claim_to_the_follow_up(database):
    async def body(db):
        started, start = fake_start()
        with patch.object(cloud_run, "start", start):
            assert await runs.claim(WS, "sync", 3) is None
            assert await runs.finish(WS, "sync", "entities", 3) == "operations/1"
            mode, chain, token = started[0]
            assert (mode, chain) == ("entities", 4)
            assert (await runs.request(WS, "topics"))["reason"] == "already_running"  # nothing slips in
            assert await runs.claim(WS, "entities", 4, token) is None
            assert await runs.finish(WS, "entities", "entities", runs.MAX_CHAIN) is None  # the chain stops
            assert len(started) == 1 and await runs.claim(WS, "topics") is None  # and the workspace is free
    with_database(database, body)


def test_a_failed_start_frees_the_claim(database):
    async def body(db):
        with patch.object(cloud_run, "start", AsyncMock(side_effect=RuntimeError("down"))):
            with pytest.raises(RuntimeError):
                await runs.request(WS, "sync")
            assert await runs.claim(WS, "topics") is None
            with pytest.raises(RuntimeError):
                await runs.finish(WS, "topics", "entities", 1)
        assert await runs.claim(WS, "sync") is None  # neither topics nor the failed follow-up holds it
    with_database(database, body)


def test_concurrent_requests_start_exactly_one_run(database):
    """The lock and the check-and-claim go in one round trip; ten requests at once still claim once."""
    from horology_runtime.database import Database

    async def body(db):
        started, start = fake_start()
        async with Database(database, 5) as wide:  # five connections, so the requests really overlap
            graph_core.configure(wide)
            with patch.object(cloud_run, "start", start):
                replies = await asyncio.gather(*(runs.request(WS, mode) for mode in ("sync", "entities", "topics") * 3 + ("sync",)))
            graph_core.configure(db)
        assert sum(r["started"] for r in replies) == 1 and len(started) == 1
        assert {r["reason"] for r in replies if not r["started"]} <= {"already_running", "cooldown"}
    with_database(database, body)
