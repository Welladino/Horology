"""Shared authenticated client_id and quota enforcement for every integration."""
from mcp.server.auth.middleware.auth_context import get_access_token
from policy import Denied, authorize


class ToolAccess:
    def __init__(self, policy, quotas, cache):
        self.policy = policy
        self.quotas = quotas
        self.cache = cache

    def scope(self, tool):
        token = get_access_token()
        if token is None:
            raise Denied('Authentication required')
        return token.client_id, authorize(self.policy, tool)

    async def reserve(self, client_id, config, tool, provider='', cost=0):
        await self.quotas.reserve(client_id, tool, provider, cost, self.policy.get('budgets', {}).get(provider))


def current_client_id():
    token = get_access_token()
    return token.client_id if token else None
