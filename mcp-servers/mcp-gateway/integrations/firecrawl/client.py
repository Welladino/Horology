"""Restricted firecrawl integration."""
from policy import Denied, credential
from shared.http import request
from shared.text import clean_text


from shared.urls import public_url

async def firecrawl_scrape(url):
    data = await request('POST', 'https://api.firecrawl.dev/v2/scrape', token=credential('FIRECRAWL_API_KEY'), body={'url': url, 'formats': ['markdown'], 'onlyMainContent': True, 'parsers': [], 'actions': [], 'proxy': 'basic', 'skipTlsVerification': False, 'timeout': 20000})
    if not data.get('success'):
        raise Denied('Scrape failed; reservation retained')
    return {'url': url, 'markdown': clean_text(data.get('data', {}).get('markdown'), 30_000)}
