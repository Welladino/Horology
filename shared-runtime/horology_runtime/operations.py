"""Signature-preserving sync/async operation instrumentation."""
import functools
import inspect
import json
import re
import time
import uuid
from contextvars import ContextVar
from .logging import logger
from .error_handling import SafeToolError, category

_trace_id = ContextVar('horology_trace_id', default=None)


class TraceMiddleware:
    """Keep Cloud Run's trace id for this request, so tool logs join its request log exactly."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers') or [])
        # X-Cloud-Trace-Context: TRACE_ID/SPAN_ID;o=1, or W3C traceparent: 00-TRACE_ID-SPAN_ID-01
        match = (re.match(rb'([0-9a-f]{32})/', headers.get(b'x-cloud-trace-context', b''))
                 or re.match(rb'00-([0-9a-f]{32})-', headers.get(b'traceparent', b'')))
        token = _trace_id.set(match.group(1).decode() if match else None)
        try:
            await self.app(scope, receive, send)
        finally:
            _trace_id.reset(token)


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
            if _trace_id.get():
                event['trace_id'] = _trace_id.get()
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
