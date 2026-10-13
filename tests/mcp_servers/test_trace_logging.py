"""Tool logs carry Cloud Run's trace id so they join their request log exactly."""
import asyncio
import json
from unittest.mock import patch

import pytest

from horology_runtime import operations


@operations.observe('test')
async def sample_tool():
    return 'ok'


def run_request(headers):
    async def app(scope, receive, send):
        await sample_tool()
    middleware = operations.TraceMiddleware(app)
    with patch.object(operations.logger, 'info') as info:
        asyncio.run(middleware({'type': 'http', 'headers': headers}, None, None))
    return json.loads(info.call_args.args[0])


TRACE = '21846654d489b2ed1fe667b7e8f32c87'


@pytest.mark.parametrize('headers', [
    [(b'x-cloud-trace-context', f'{TRACE}/123;o=1'.encode())],
    [(b'traceparent', f'00-{TRACE}-00f067aa0ba902b7-01'.encode())],
])
def test_tool_log_includes_request_trace(headers):
    assert run_request(headers)['trace_id'] == TRACE


@pytest.mark.parametrize('headers', [[], [(b'x-cloud-trace-context', b'not-a-trace')]])
def test_tool_log_omits_missing_or_malformed_trace(headers):
    assert 'trace_id' not in run_request(headers)
