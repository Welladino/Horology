"""Register restricted firecrawl MCP tools."""
import asyncio
import hashlib
import json
import re

from horology_runtime.operations import observe
from policy import Denied, credential
from shared.access import current_client_id
from . import client, client_alexandria


def register_tools(mcp, access):
    policy, cache = access.policy, access.cache
    scope, reserve = access.scope, access.reserve

    @mcp.tool()
    @observe("firecrawl", current_client_id)
    async def firecrawl_scrape_page(url: str) -> dict:
        """Scrape one public HTTPS URL, with no crawl or browser actions."""
        client_id, config = scope('firecrawl_scrape_page')
        if policy.get('firecrawl', {}).get('url_policy') != 'public_https':
            raise Denied('Public HTTPS scrape policy is not configured')
        await asyncio.to_thread(client.public_url, url)
        credential('FIRECRAWL_API_KEY')
        cost = policy.get('firecrawl', {}).get('scrape_credits')
        if cost != 1:
            raise Denied('Basic scrape cost must be verified before use')
        key = hashlib.sha256(json.dumps(['firecrawl', url]).encode()).hexdigest()
        cached = await cache.cached(client_id, key)
        if cached is not None:
            await reserve(client_id, config, 'firecrawl_scrape_page')
            return cached
        await reserve(client_id, config, 'firecrawl_scrape_page', 'firecrawl', cost)
        data = await client.firecrawl_scrape(url)
        await cache.save_cache(client_id, key, data)
        return data



    async def run_alexandria(tool, operation, options, client_id, config):
        client_alexandria.check(policy, config, operation)
        credential('FIRECRAWL_API_KEY')
        key = hashlib.sha256(json.dumps([operation, options], sort_keys=True).encode()).hexdigest()
        cached = await cache.cached(client_id, key)
        if cached is not None:
            await reserve(client_id, config, tool)
            return cached
        await client_alexandria.verify_price(operation)
        await reserve(client_id, config, tool, 'firecrawl', 5)
        data = await client_alexandria.execute(operation, options)
        await cache.save_cache(client_id, key, data)
        return data


    @mcp.tool()
    @observe("firecrawl", current_client_id)
    async def firecrawl_discover_tools() -> dict:
        """Read free metadata for only the fixed Shopify, Alibaba and trends contracts."""
        client_id, config = scope('firecrawl_discover_tools')
        credential('FIRECRAWL_API_KEY')
        await reserve(client_id, config, 'firecrawl_discover_tools')
        return await client_alexandria.discover()

    @mcp.tool()
    @observe("firecrawl", current_client_id)
    async def firecrawl_shopify_search(query: str, country: str, limit: int = 5) -> dict:
        """Search the global public Shopify catalog in an approved market; 5 credits."""
        client_id, config = scope('firecrawl_shopify_search')
        client_alexandria.query_text(query)
        client_alexandria.country_check(policy, config, country)
        if not 1 <= limit <= 5:
            raise Denied('At most five products are allowed')
        data = await run_alexandria('firecrawl_shopify_search', 'shopify_search', {'query':query,'country':country,'limit':limit}, client_id, config)
        for product in data.get('products', [])[:5]:
            if isinstance(product, dict) and isinstance(product.get('id'), str):
                await cache.save_cache(client_id, client_alexandria.product_key('shopify', product['id'], country), {'seen':True})
        return data

    @mcp.tool()
    @observe("firecrawl", current_client_id)
    async def firecrawl_shopify_product(product_id: str, country: str) -> dict:
        """Read one product returned by this client_id's recent Shopify search; 5 credits."""
        client_id, config = scope('firecrawl_shopify_product')
        client_alexandria.country_check(policy, config, country)
        if not product_id or len(product_id) > 500 or not await cache.cached(client_id, client_alexandria.product_key('shopify', product_id, country)):
            raise Denied('Use an ID returned by this client_id within the last hour')
        return await run_alexandria('firecrawl_shopify_product', 'shopify_product', {'product_id':product_id,'country':country}, client_id, config)

    @mcp.tool()
    @observe("firecrawl", current_client_id)
    async def firecrawl_alibaba_search(query: str) -> dict:
        """Read the first public Alibaba result page; mainly sponsored, no stock guarantee; 5 credits."""
        client_id, config = scope('firecrawl_alibaba_search')
        client_alexandria.query_text(query)
        data = await run_alexandria('firecrawl_alibaba_search', 'alibaba_search', {'query':query}, client_id, config)
        for product in data.get('records', [])[:5]:
            if isinstance(product, dict) and isinstance(product.get('url'), str):
                await cache.save_cache(client_id, client_alexandria.product_key('alibaba', product['url']), {'seen':True})
        data['records'] = data.get('records', [])[:5]
        return data

    @mcp.tool()
    @observe("firecrawl", current_client_id)
    async def firecrawl_alibaba_product(url: str) -> dict:
        """Read one listing returned by this client_id's recent Alibaba search; 5 credits."""
        client_id, config = scope('firecrawl_alibaba_product')
        if not re.fullmatch(r'https://www\.alibaba\.com/product-detail/[A-Za-z0-9-]+_[0-9]{1,20}\.html', url) or not await cache.cached(client_id, client_alexandria.product_key('alibaba', url)):
            raise Denied('Use an Alibaba listing returned by this client_id within the last hour')
        return await run_alexandria('firecrawl_alibaba_product', 'alibaba_product', {'url':url}, client_id, config)

    @mcp.tool()
    @observe("firecrawl", current_client_id)
    async def firecrawl_trends(keywords: list[str], country: str, time_range: str = 'today 12-m') -> dict:
        """Compare 1–5 approved-market search terms over a bounded time range; 5 credits."""
        client_id, config = scope('firecrawl_trends')
        client_alexandria.country_check(policy, config, country)
        if not 1 <= len(keywords) <= 5 or len(set(keywords)) != len(keywords):
            raise Denied('Provide 1–5 distinct keywords')
        for keyword in keywords:
            client_alexandria.query_text(keyword)
        if time_range not in ('now 1-d', 'now 7-d', 'today 1-m', 'today 3-m', 'today 12-m'):
            raise Denied('Unsupported time range')
        return await run_alexandria('firecrawl_trends', 'trends', {'keywords':keywords,'geo':country,'time':time_range,'property':'web','category':0}, client_id, config)
