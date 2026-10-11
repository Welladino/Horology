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
