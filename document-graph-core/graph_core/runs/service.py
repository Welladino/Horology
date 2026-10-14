"""Sync-job runs: one at a time per workspace, a cooldown on agent requests, and follow-up runs.

An accepted request claims the workspace straight away and passes a token to
the job, which confirms the claim when it starts; so nothing else can start in
between. When a run's cap leaves work over, it hands the claim to the next run
it starts, at most MAX_CHAIN runs in a row.
"""
import uuid

from .. import database
from . import cloud_run
from .repository import RunRepository

MODES = cloud_run.MODES
COOLDOWN_SECONDS = 300  # an agent can ask for the same run once per 5 minutes
STALE_MINUTES = 70  # the job's time limit is 60 minutes: a confirmed claim older than this crashed
START_MINUTES = 10  # a claim the job never confirmed (it didn't start) expires after this
MAX_CHAIN = 10  # follow-up runs in a row (10 runs x 30 documents); then it stops and reports what's left


def _repository():
    return RunRepository(database.get(), STALE_MINUTES, START_MINUTES)


async def request(workspace, mode):
    """Start a run for an agent, unless one is running or the same run was asked for recently."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    repository = _repository()
    token = uuid.uuid4().hex
    refused = await repository.request(workspace, mode, COOLDOWN_SECONDS, token)
    if refused and refused[0] == "running":
        return {"started": False, "reason": "already_running", "running": refused[1],
                "next_step": "A run is in progress for this workspace; results appear in the sheet when it ends."}
    if refused:
        return {"started": False, "reason": "cooldown", "retry_after_seconds": refused[1]}
    try:
        operation = await cloud_run.start(workspace, mode, 1, token)
    except Exception:
        await repository.cancel_request(workspace, mode)
        raise
    return {"started": True, "operation": operation}


async def claim(workspace, mode, chain=1, token=None):
    """Called by the job before it works; returns the mode holding the workspace, or None once claimed."""
    return await _repository().claim(workspace, mode, chain, token)


async def release(workspace, mode):
    await _repository().release(workspace, mode)


async def finish(workspace, mode, next_mode, chain):
    """End this run: hand the workspace to a follow-up in next_mode, or release it.

    Returns the follow-up's operation, or None (no follow-up, or MAX_CHAIN reached)."""
    repository = _repository()
    if not next_mode or chain >= MAX_CHAIN:
        await repository.release(workspace, mode)
        return None
    token = uuid.uuid4().hex
    await repository.hand_over(workspace, mode, next_mode, chain + 1, token)
    try:
        return await cloud_run.start(workspace, next_mode, chain + 1, token)
    except Exception:
        await repository.release(workspace, next_mode)
        raise
