"""Single source of timeout policy; values are seconds unless suffixed _ms."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TimeoutPolicy:
    gateway_http: int = 25
    openrouter_http: int = 30
    database_connect: int = 5
    supabase_statement_ms: int = 3000
    neon_statement_ms: int = 10000
    neon_lock_ms: int = 3000

    @property
    def neon_options(self):
        return f"-c statement_timeout={self.neon_statement_ms} -c lock_timeout={self.neon_lock_ms}"


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


def gateway_public_url():
    """Base URL advertised in gateway auth metadata; never a credential URL."""
    import os
    from urllib.parse import urlsplit
    port = http_server_options(8767, 'GATEWAY_BIND', '127.0.0.1')['port']
    value = os.environ.get('GATEWAY_PUBLIC_URL', f'http://localhost:{port}').rstrip('/')
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('GATEWAY_PUBLIC_URL must be a base URL without credentials, path, query or fragment')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')):
        raise ValueError('GATEWAY_PUBLIC_URL must use HTTPS outside localhost')
    return value


@dataclass(frozen=True)
class OAuthPolicy:
    login_seconds: int = 600
    code_seconds: int = 120
    access_seconds: int = 900
    refresh_seconds: int = 86400 * 7
    client_seconds: int = 86400 * 90


OAUTH = OAuthPolicy()
