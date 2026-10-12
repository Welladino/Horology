"""Fixed read-only Alexandria contracts; agents cannot choose provider operations."""
import hashlib
import json
import re
from policy import Denied, credential
from shared.http import request
from shared.text import clean_text

CONTRACTS = {
    'shopify_search': ('shopify', 'catalog/search_catalog', 5),
    'shopify_product': ('shopify', 'catalog/get_product', 5),
    'alibaba_search': ('alibaba', 'retail/search', 5),
    'alibaba_product': ('alibaba', 'retail/product', 5),
    'trends': ('firecrawl-trends', 'trends/interest_over_time', 5),
}


def bounded(value, depth=0):
    if depth > 6:
        return None
    if isinstance(value, str):
        return clean_text(value, 2000)
    if isinstance(value, list):
        return [bounded(v, depth+1) for v in value[:100]]
    if isinstance(value, dict):
        return {str(k)[:100]: bounded(v, depth+1) for k, v in list(value.items())[:30]}
    return value


def check(policy, config, operation):
    if operation not in CONTRACTS or operation not in policy.get('alexandria', {}).get('operations', []) or operation not in config.get('alexandria_operations', []):
        raise Denied('Alexandria operation is outside shared access scope')


def query_text(query):
    if not query.strip() or len(query) > 200:
        raise Denied('Provide a query of 1–200 characters')


def country_check(policy, config, country):
    if not re.fullmatch('[A-Z]{2}', country) or country not in policy.get('alexandria', {}).get('countries', []) or country not in config.get('alexandria_countries', []):
        raise Denied('Market is outside shared access scope')


def product_key(provider, value, country=''):
    return 'alexandria-product-' + hashlib.sha256(json.dumps([provider, value, country]).encode()).hexdigest()


async def execute(operation, options):
    provider, capability, _ = CONTRACTS[operation]
    data = await request('POST', 'https://api.firecrawl.dev/v2/scrape', token=credential('FIRECRAWL_API_KEY'), body={'alexandria': [{'provider': provider, 'capability': capability, 'options': options}], 'timeout': 20000})
    if not data.get('success'):
        raise Denied('Alexandria request failed; reservation retained')
    entries = data.get('data', {}).get('alexandria', [])
    if len(entries) != 1 or entries[0].get('provider') != provider or entries[0].get('capability') != capability or not isinstance(entries[0].get('data'), dict):
        raise Denied('Unexpected Alexandria response')
    result = bounded(entries[0]['data'])
    result['truncated'] = result != entries[0]['data']
    return result


async def verify_price(operation):
    provider, capability, cost = CONTRACTS[operation]
    data = await request('POST', 'https://api.firecrawl.dev/v2/scrape', token=credential('FIRECRAWL_API_KEY'), body={'alexandria': [{'provider': 'firecrawl', 'capability': 'find-tools', 'options': {'providers': [provider], 'capabilities': [capability], 'limit': 1, 'expand': [], 'level': 'tools'}}]})
    entries = data.get('data', {}).get('alexandria', [])
    if not data.get('success') or len(entries) != 1 or entries[0].get('provider') != 'firecrawl' or entries[0].get('capability') != 'find-tools':
        raise Denied('Cannot verify current Alexandria price')
    items = entries[0].get('data', {}).get('items', [])
    if len(items) != 1 or items[0].get('provider') != provider or items[0].get('capability') != capability or type(items[0].get('creditsCost')) is not int or items[0]['creditsCost'] != cost or items[0].get('perRecord') is not False:
        raise Denied('Alexandria price changed or is unknown; operator review required')


async def discover():
    # No arbitrary discovery query or selector. The free endpoint returns metadata only.
    data = await request('POST', 'https://api.firecrawl.dev/v2/scrape', token=credential('FIRECRAWL_API_KEY'), body={'alexandria': [{'provider': 'firecrawl', 'capability': 'find-tools', 'options': {'providers': ['shopify', 'alibaba', 'firecrawl-trends'], 'capabilities': [v[1] for v in CONTRACTS.values()], 'limit': 5, 'expand': [], 'level': 'tools'}}]})
    if not data.get('success'):
        raise Denied('Catalogue discovery failed')
    entries = data.get('data', {}).get('alexandria', [])
    if len(entries) != 1 or entries[0].get('provider') != 'firecrawl' or entries[0].get('capability') != 'find-tools':
        raise Denied('Unexpected catalogue response')
    return {'tools': [{k: bounded(item.get(k)) for k in ('provider','capability','name','description','creditsCost','perRecord')} for item in entries[0].get('data', {}).get('items', [])[:5] if (item.get('provider'), item.get('capability')) in [(p,c) for p,c,_ in CONTRACTS.values()]]}
