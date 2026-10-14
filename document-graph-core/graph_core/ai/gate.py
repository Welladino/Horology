"""At most MAX_CALLS AI requests in flight per process, whoever makes them, so callers can run
work in parallel without overrunning the provider's rate limits or the database pool."""
import asyncio

MAX_CALLS = 3
_gates = {}


def gate():
    """This event loop's semaphore (a semaphore can't be shared across loops, e.g. between tests)."""
    loop = asyncio.get_running_loop()
    if loop not in _gates:
        _gates.clear()
        _gates[loop] = asyncio.Semaphore(MAX_CALLS)
    return _gates[loop]
