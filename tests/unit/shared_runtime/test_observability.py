"""Sanitized MCP failures, structured logs and preserved tool signatures.

All failures are injected; no provider, DB or paid requests are made.
"""
import asyncio
import inspect
import json
import sys
from unittest.mock import patch

import httpx
import psycopg
import pytest

from horology_runtime.operations import SafeToolError, observe


@pytest.mark.parametrize('error, expected', [
    (httpx.ReadTimeout('secret-token and document text'), 'timeout'),
    (httpx.ConnectError('postgresql://user:password@private-host/db'), 'connection_failed'),
    (psycopg.OperationalError('password and raw DSN'), 'connection_failed'),
    (ValueError('sensitive input'), 'invalid_input'),
])
def test_async_errors_are_sanitized_and_correlated(error, expected):
    async def failing(value: str) -> dict:
        raise error
    wrapped = observe('test', lambda: 'approved-assignment')(failing)
    assert inspect.signature(wrapped) == inspect.signature(failing)
    with patch('horology_runtime.operations.logger.info') as log:
        with pytest.raises(SafeToolError) as caught:
            asyncio.run(wrapped('do-not-log-this'))
    event = json.loads(log.call_args.args[0])
    assert event['error_category'] == expected
    assert event['request_id'] == caught.value.request_id
    assert event['client_id'] == 'approved-assignment'
    assert event['outcome'] == 'error'
    assert 'do-not-log-this' not in str(event)
    assert str(error) not in str(caught.value)
    assert str(error) not in str(event)


def test_sync_success_does_not_log_document_content():
    @observe('document_graph')
    def read_document(document_id: int) -> dict:
        return {'content': 'private document content'}
    with patch('horology_runtime.operations.logger.info') as log:
        assert read_document(17)['content'] == 'private document content'
    event = json.loads(log.call_args.args[0])
    assert event['outcome'] == 'success'
    assert event['duration_ms'] >= 0
    assert 'private document content' not in str(event)


def test_json_lines_carry_severity_and_leave_tracebacks_out():
    import logging
    from horology_runtime.logging import JsonLines
    try:
        raise RuntimeError('private document content')
    except RuntimeError:
        record = logging.LogRecord('graph_core.entities', logging.WARNING, __file__, 1,
                                   'entities for document %s failed: %s', (41, 'timeout'), sys.exc_info())
    line = json.loads(JsonLines().format(record))
    assert line == {'severity': 'WARNING', 'logger': 'graph_core.entities',
                    'message': 'entities for document 41 failed: timeout'}
