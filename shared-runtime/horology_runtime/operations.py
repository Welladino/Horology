"""Signature-preserving sync/async operation instrumentation."""
import functools
import inspect
import json
import time
import uuid
from .logging import logger
from .error_handling import SafeToolError, category

def observe(integration, client_id=None):
    """Preserve tool signatures; never log args, results or exception messages."""
    def decorate(fn):
        def start():
            return uuid.uuid4().hex, time.monotonic()

        def finish(request_id, started, outcome, error_category=None):
            event = {'event': 'runtime_operation', 'request_id': request_id,
                     'tool': fn.__name__, 'integration': integration,
                     'duration_ms': round((time.monotonic() - started) * 1000, 2),
                     'outcome': outcome}
            if client_id:
                # Only a authenticated client identifier, never the token.
                event['client_id'] = client_id()
            if error_category:
                event['error_category'] = error_category
            logger.info(json.dumps(event, separators=(',', ':')))

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def wrapped(*args, **kwargs):
                request_id, started = start()
                try:
                    result = await fn(*args, **kwargs)
                except Exception as error:
                    code = category(error)
                    finish(request_id, started, 'error', code)
                    raise SafeToolError(code, request_id) from None
                finish(request_id, started, 'success')
                return result
        else:
            @functools.wraps(fn)
            def wrapped(*args, **kwargs):
                request_id, started = start()
                try:
                    result = fn(*args, **kwargs)
                except Exception as error:
                    code = category(error)
                    finish(request_id, started, 'error', code)
                    raise SafeToolError(code, request_id) from None
                finish(request_id, started, 'success')
                return result
        return wrapped
    return decorate
