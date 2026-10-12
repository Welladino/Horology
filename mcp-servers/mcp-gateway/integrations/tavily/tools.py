from horology_runtime.operations import observe
from shared.access import current_client_id
"""Register restricted tavily MCP tools."""
from . import client
import hashlib
import json
from policy import Denied


def register_tools(mcp, access):
    policy, cache = access.policy, access.cache
    scope, reserve = access.scope, access.reserve

    @mcp.tool()
    @observe("tavily", current_client_id)
    async def tavily_search(query: str, advanced: bool = False) -> list[dict]:
        """Search at most five results. Basic costs 1 credit; advanced costs 2."""
        tool = 'tavily_advanced_search' if advanced else 'tavily_search'
        client_id, config = scope(tool)
        if not query.strip() or len(query) > 400:
            raise Denied('Search query must contain 1–400 characters')
        # Check credential before reserving; never read it into tool responses.
        from policy import credential
        credential('TAVILY_API_KEY')
        key = hashlib.sha256(json.dumps([tool, query]).encode()).hexdigest()
        cached = await cache.cached(client_id, key)
        if cached is not None:
            await reserve(client_id, config, tool)
            return cached
        await reserve(client_id, config, tool, 'tavily', 2 if advanced else 1)
        data = await client.tavily(query, advanced)
        await cache.save_cache(client_id, key, data)
        return data


    @mcp.tool()
    @observe("tavily", current_client_id)
    async def tavily_extract_pages(urls: list[str]) -> dict:
        """Basic extraction of 1–5 exact approved public URLs; reserves 1 credit."""
        import asyncio
        from shared.urls import approved_url
        from policy import credential
        client_id, config = scope('tavily_extract_pages')
        if not 1 <= len(urls) <= 5 or len(set(urls)) != len(urls):
            raise Denied('Provide 1–5 distinct approved URLs')
        for url in urls:
            await asyncio.to_thread(approved_url, policy, config, url, 'tavily')
        credential('TAVILY_API_KEY')
        key = hashlib.sha256(json.dumps(['tavily_extract', urls]).encode()).hexdigest()
        cached = await cache.cached(client_id, key)
        if cached is not None:
            await reserve(client_id, config, 'tavily_extract_pages')
            return cached
        await reserve(client_id, config, 'tavily_extract_pages', 'tavily', 1)
        data = await client.extract(urls)
        await cache.save_cache(client_id, key, data)
        return data
