from horology_runtime.operations import observe
from shared.access import current_assignment
"""Register restricted tavily MCP tools."""
from . import client
import hashlib
import json
from policy import Denied


def register_tools(mcp, access):
    policy, ledger = access.policy, access.ledger
    scope, reserve = access.scope, access.reserve

    @mcp.tool()
    @observe("tavily", current_assignment)
    async def tavily_search(query: str, advanced: bool = False) -> list[dict]:
        """Search at most five results. Basic costs 1 credit; advanced costs 2."""
        tool = 'tavily_advanced_search' if advanced else 'tavily_search'
        assignment, config = scope(tool)
        if not query.strip() or len(query) > 400:
            raise Denied('Search query must contain 1–400 characters')
        # Check credential before reserving; never read it into tool responses.
        from policy import credential
        credential('TAVILY_API_KEY')
        key = hashlib.sha256(json.dumps([tool, query]).encode()).hexdigest()
        cached = ledger.cached(assignment, key)
        if cached is not None:
            reserve(assignment, config, tool)
            return cached
        reserve(assignment, config, tool, 'tavily', 2 if advanced else 1)
        data = await client.tavily(query, advanced)
        ledger.save_cache(assignment, key, data)
        return data
