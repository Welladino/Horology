"""Restricted firecrawl integration."""
from urllib.parse import urlparse
from policy import Denied, credential
from shared.http import request
from shared.text import clean_text


def approved_url(policy, config, url):
    import ipaddress
    import socket
    parsed = urlparse(url)
    if url not in policy.get('firecrawl', {}).get('approved_urls', []) or url not in config.get('approved_urls', []):
        raise Denied('URL must be explicitly approved by the operator')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.fragment:
        raise Denied('Only approved public HTTPS pages are supported')
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443)
    except socket.gaierror:
        raise Denied('Cannot verify public target address') from None
    if not addresses or any(not ipaddress.ip_address(record[4][0]).is_global for record in addresses):
        raise Denied('Private and reserved target addresses are forbidden')

async def firecrawl_scrape(url):
    data = await request('POST', 'https://api.firecrawl.dev/v2/scrape', token=credential('FIRECRAWL_API_KEY'), body={'url': url, 'formats': ['markdown'], 'onlyMainContent': True, 'parsers': [], 'actions': [], 'proxy': 'basic', 'skipTlsVerification': False, 'timeout': 20000})
    if not data.get('success'):
        raise Denied('Scrape failed; reservation retained')
    return {'url': url, 'markdown': clean_text(data.get('data', {}).get('markdown'), 30_000)}
