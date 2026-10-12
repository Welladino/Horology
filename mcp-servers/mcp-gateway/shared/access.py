"""Shared authenticated assignment and quota enforcement for every integration."""
from mcp.server.auth.middleware.auth_context import get_access_token
from policy import Denied, authorize


class ToolAccess:
    def __init__(self, policy, ledger):
        self.policy = policy
        self.ledger = ledger

    def scope(self, tool):
        token = get_access_token()
        if token is None:
            raise Denied('Authentication required')
        assignment = (token.claims or {}).get('assignment', token.client_id)
        return assignment, authorize(self.policy, assignment, tool)

    def reserve(self, assignment, config, tool, provider='', cost=0):
        self.ledger.reserve(assignment, tool, config.get('limits', {}).get(tool, 0), provider, cost, self.policy.get('budgets', {}).get(provider))


def current_assignment():
    token = get_access_token()
    return (token.claims or {}).get('assignment', token.client_id) if token else None
