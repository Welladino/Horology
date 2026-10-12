"""Shared public HTTPS boundaries; DNS and Firecrawl calls are mocked."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "mcp-servers/mcp-gateway"))
from unittest.mock import AsyncMock, patch
import pytest
from horology_runtime.urls import UnsafeURL, validate_public_https_url
from integrations.firecrawl import client as firecrawl
from test_capabilities import setup


@pytest.mark.parametrize('address', ['127.0.0.1', '10.1.2.3', '172.16.0.1', '172.31.255.255', '192.168.1.1', '169.254.169.254', '100.64.0.1', '0.0.0.0', '224.0.0.1', '::1', 'fd00::1', 'fe80::1', '::ffff:10.0.0.1', '2002:0a00:0001::1'])
def test_nonpublic_resolution_is_denied(address):
    with patch('socket.getaddrinfo', return_value=[(2,1,6,'',(address,443))]):
        with pytest.raises(UnsafeURL):
            validate_public_https_url('https://public-looking.example/page')


@pytest.mark.parametrize('url', ['http://example.com', 'https://localhost', 'https://foo.localhost', 'https://metadata.google.internal', 'https://user:secret@example.com', 'https://example.com/#fragment', 'https://example.com:0', 'https://example.com:99999', 'https://example.com/white space', 'https://example.com\\@127.0.0.1'])
def test_invalid_url_never_resolves(url):
    with patch('socket.getaddrinfo') as resolve:
        with pytest.raises(UnsafeURL):
            validate_public_https_url(url)
        resolve.assert_not_called()


def test_mixed_public_private_dns_is_denied():
    with patch('socket.getaddrinfo', return_value=[(2,1,6,'',('8.8.8.8',443)), (2,1,6,'',('10.0.0.1',443))]):
        with pytest.raises(UnsafeURL):
            validate_public_https_url('https://example.com')


def test_public_https_scrape_does_not_require_an_allowlist(setup,monkeypatch):
    policy, config, ledger, mcp = setup
    assert policy['firecrawl'].get('approved_urls') is None
    monkeypatch.setenv('FIRECRAWL_API_KEY', 'test-only')
    with patch('socket.getaddrinfo', return_value=[(2,1,6,'',('8.8.8.8',443))]), patch.object(firecrawl,'firecrawl_scrape',AsyncMock(return_value={'markdown':'page'})) as scrape:
        assert asyncio.run(mcp.tools['firecrawl_scrape_page']('https://new-public.example/page')) == {'markdown':'page'}
        scrape.assert_awaited_once()
        assert ledger.calls[0][2:4] == ('firecrawl',1)
