"""Single source of timeout policy; values are seconds unless suffixed _ms."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TimeoutPolicy:
    gateway_http: int = 25
    openrouter_http: int = 30
    database_connect: int = 5
    supabase_statement_ms: int = 3000
    # Neon statement (10 s) and lock (3 s) timeouts are login defaults: alembic 20261014_001.


TIMEOUTS = TimeoutPolicy()


def http_server_options(default_port, bind_variable, default_host):
    """Cloud Run supplies PORT; local services retain their documented defaults.

    Stateless JSON requests let any instance handle each MCP call. These tools
    do not require server notifications or in-memory session continuity.
    """
    import os
    port = int(os.environ.get('PORT', str(default_port)))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be between 1 and 65535')
    host = os.environ.get(bind_variable, '0.0.0.0' if os.environ.get('K_SERVICE') else default_host)
    return {'host': host, 'port': port, 'stateless_http': True, 'json_response': True}


def service_public_url(variable, default_port, bind_variable, default_host):
    """Base URL a service advertises in its auth metadata; never a credential URL."""
    import os
    from urllib.parse import urlsplit
    port = http_server_options(default_port, bind_variable, default_host)['port']
    value = os.environ.get(variable, f'http://localhost:{port}').rstrip('/')
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError(f'{variable} must be a base URL without credentials, path, query or fragment')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')):
        raise ValueError(f'{variable} must use HTTPS outside localhost')
    return value


def gateway_public_url():
    return service_public_url('GATEWAY_PUBLIC_URL', 8767, 'GATEWAY_BIND', '127.0.0.1')


def document_graph_public_url():
    return service_public_url('DOCUMENT_GRAPH_PUBLIC_URL', 8765, 'DOCUMENT_GRAPH_BIND', '0.0.0.0')


@dataclass(frozen=True)
class OAuthPolicy:
    login_seconds: int = 600
    code_seconds: int = 120
    access_seconds: int = 900
    refresh_seconds: int = 86400 * 7
    client_seconds: int = 86400 * 90
    # Verified access tokens are remembered in memory to skip the database lookup.
    # A token revoked outside this process (scripts/revoke_email.py) keeps working
    # until its entry expires; a restart or new revision clears it at once.
    access_cache_seconds: int = 300
    access_cache_size: int = 256


OAUTH = OAuthPolicy()


@dataclass(frozen=True)
class DatabasePolicy:
    gateway_pool_size: int = 4
    document_graph_pool_size: int = 4
    supabase_pool_size: int = 2


DATABASE = DatabasePolicy()
