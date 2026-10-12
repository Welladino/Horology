"""Safe failure categories usable with or without HTTP/Postgres libraries."""
import json

try:
    import httpx
except ImportError:
    httpx = None
try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import psycopg
    from psycopg_pool import PoolTimeout
except ImportError:
    psycopg = None
    PoolTimeout = None

class SafeToolError(RuntimeError):
    """Only a category and correlation ID may reach an MCP client."""
    def __init__(self, category, request_id):
        self.category = category
        self.request_id = request_id
        super().__init__(f"{category}; request_id={request_id}")

def category(error):
    if isinstance(error, SafeToolError):
        return error.category
    if isinstance(error, TimeoutError) or (httpx and isinstance(error, httpx.TimeoutException)) or (psycopg2 and isinstance(error, psycopg2.errors.QueryCanceled)):
        return 'timeout'
    if psycopg and isinstance(error, (psycopg.errors.QueryCanceled, PoolTimeout)):
        return 'timeout'
    if psycopg and isinstance(error, (psycopg.OperationalError, psycopg.InterfaceError)):
        return 'connection_failed'
    if httpx and isinstance(error, httpx.HTTPStatusError):
        return 'provider_rejected'
    if (httpx and isinstance(error, httpx.RequestError)) or (psycopg2 and isinstance(error, (psycopg2.OperationalError, psycopg2.InterfaceError))):
        return 'connection_failed'
    if type(error).__name__ == 'Denied':
        message = str(error)
        if 'HTTP ' in message:
            return 'provider_rejected'
        if any(word in message for word in ('budget', 'limit exhausted')):
            return 'quota_denied'
        return 'permission_denied'
    if isinstance(error, (json.JSONDecodeError, KeyError, IndexError)):
        return 'invalid_provider_response'
    if isinstance(error, ValueError):
        return 'invalid_input'
    if psycopg and isinstance(error, psycopg.Error):
        return 'database_failed'
    if psycopg2 and isinstance(error, psycopg2.Error):
        return 'database_failed'
    return 'operation_failed'
