from horology_runtime.operations import observe
from shared.access import current_assignment
"""Register restricted firecrawl MCP tools."""
from . import client
import asyncio
import hashlib
import json
from policy import Denied


def register_tools(mcp, access):
    policy, ledger = access.policy, access.ledger
    scope, reserve = access.scope, access.reserve

    @mcp.tool()
    @observe("firecrawl", current_assignment)
    async def firecrawl_scrape_page(url: str) -> dict:
        """Scrape one operator-approved public URL, with no crawl or browser actions."""
        assignment, config = scope('firecrawl_scrape_page')
        await asyncio.to_thread(client.approved_url, policy, config, url)
        from policy import credential
        credential('FIRECRAWL_API_KEY')
        cost = policy.get('firecrawl', {}).get('scrape_credits')
        if cost != 1:
            raise Denied('Basic scrape cost must be verified before use')
        key = hashlib.sha256(json.dumps(['firecrawl', url]).encode()).hexdigest()
        cached = ledger.cached(assignment, key)
        if cached is not None:
            reserve(assignment, config, 'firecrawl_scrape_page')
            return cached
        reserve(assignment, config, 'firecrawl_scrape_page', 'firecrawl', cost)
        data = await client.firecrawl_scrape(url)
        ledger.save_cache(assignment, key, data)
        return data
