"""Retry an AI request that failed for a reason that passes: a timeout, a dropped connection,
a rate limit (429) or a server error (5xx). Other failures (400, 401, 403 such as the
content filter) are raised at once, since trying again gives the same answer."""
import asyncio
import logging
import random

import httpx
from horology_runtime.error_handling import category

ATTEMPTS = 3  # the first try plus two retries
WAITS = (1, 3)  # seconds before each retry, plus up to 0.5 s of jitter
MAX_RETRY_AFTER = 30  # a provider's Retry-After above this is capped
sleep = asyncio.sleep  # patched in tests
log = logging.getLogger("graph_core.ai")


def should_retry(error):
    if isinstance(error, httpx.TransportError):  # includes every timeout
        return True
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return status == 429 or status >= 500
    return False


def _wait(error, attempt):
    if isinstance(error, httpx.HTTPStatusError):
        try:
            return min(float(error.response.headers.get("retry-after", "")), MAX_RETRY_AFTER)
        except ValueError:
            pass
    return WAITS[attempt] + random.uniform(0, 0.5)  # nosec B311: retry jitter, not security


async def call(request):
    """Await request() up to ATTEMPTS times; request is a no-argument coroutine function."""
    for attempt in range(ATTEMPTS):
        try:
            return await request()
        except Exception as error:
            if attempt == ATTEMPTS - 1 or not should_retry(error):
                raise
            wait = _wait(error, attempt)
            # Shows how often providers are slow; the category only, never the message.
            log.warning("AI request retry %s of %s after %s, waiting %.1fs", attempt + 1, ATTEMPTS - 1, category(error), wait)
            await sleep(wait)
