"""Regression tests for paid-tool budgets, fixed contracts and narrow write boundaries.

All external provider calls are mocked; real Postgres accounting is tested elsewhere.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

ROOT = Path(__file__).resolve().parents[3] / 'mcp-servers/mcp-gateway'
sys.path.insert(0, str(ROOT))
from integrations.firecrawl import client_alexandria as alexandria, tools as firecrawl_tools
from integrations.tavily import tools as tavily_tools, client as tavily
from policy import Denied, load_policy
from shared.access import ToolAccess
from horology_runtime.operations import SafeToolError


class MCP:
    def __init__(self):
        self.tools = {}
    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class Ledger:
    def __init__(self):
        self.calls = []
        self.cache = {}
    async def reserve(self, *args):
        self.calls.append(args)
    async def cached(self, assignment, key):
        return self.cache.get((assignment,key))
    async def save_cache(self, assignment, key, value):
        self.cache[assignment,key] = value


@pytest.fixture
def setup():
    policy = load_policy(ROOT/'config/policy.example.json')
    config = policy['access']
    ledger, mcp = Ledger(), MCP()
    access = ToolAccess(policy,ledger,ledger)
    access.scope = lambda tool: ('test',config)
    firecrawl_tools.register_tools(mcp,access)
    tavily_tools.register_tools(mcp,access)
    return policy,config,ledger,mcp


def test_alexandria_validates_contract_price_before_paid_execution(setup,monkeypatch):
    policy,config,ledger,mcp = setup
    monkeypatch.setenv('FIRECRAWL_API_KEY','test-only')
    with patch.object(alexandria,'verify_price',new_callable=AsyncMock,side_effect=Denied('price changed')), patch.object(alexandria,'execute',new_callable=AsyncMock) as execute:
        with pytest.raises(SafeToolError):
            asyncio.run(mcp.tools['firecrawl_shopify_search']('mugs','SG'))
        execute.assert_not_called()
        assert ledger.calls == []


def test_alexandria_reserves_five_and_cache_does_not_spend_again(setup,monkeypatch):
    policy,config,ledger,mcp = setup
    monkeypatch.setenv('FIRECRAWL_API_KEY','test-only')
    with patch.object(alexandria,'verify_price',new_callable=AsyncMock), patch.object(alexandria,'execute',new_callable=AsyncMock,return_value={'products':[{'id':'gid://shopify/Product/1'}]}) as execute:
        async def run():
            await mcp.tools['firecrawl_shopify_search']('mugs','SG')
            await mcp.tools['firecrawl_shopify_search']('mugs','SG')
        asyncio.run(run())
        assert execute.await_count == 1
        assert ledger.calls[0][2:4] == ('firecrawl',5)
        assert ledger.calls[1][2:4] == ('',0)


def test_market_and_unseen_product_never_execute(setup,monkeypatch):
    policy,config,ledger,mcp = setup
    monkeypatch.setenv('FIRECRAWL_API_KEY','test-only')
    with patch.object(alexandria,'execute',new_callable=AsyncMock) as execute:
        for name,args in [('firecrawl_shopify_search',('mugs','ZZ')),('firecrawl_shopify_search',('mugs','WORLDWIDE')),('firecrawl_shopify_product',('unseen','SG')),('firecrawl_alibaba_product',('https://www.alibaba.com/product-detail/mugs_123.html',)),('firecrawl_trends',(['mugs'],'SG','all'))]:
            with pytest.raises(SafeToolError):
                asyncio.run(mcp.tools[name](*args))
        execute.assert_not_called()
        assert not ledger.calls


def test_response_must_match_fixed_provider(monkeypatch):
    monkeypatch.setenv('FIRECRAWL_API_KEY','test-only')
    with patch.object(alexandria,'request',new_callable=AsyncMock,return_value={'success':True,'data':{'alexandria':[{'provider':'other','capability':'buy','data':{}}]}}) as request:
        with pytest.raises(Denied):
            asyncio.run(alexandria.execute('shopify_search',{'query':'mugs','country':'SG','limit':5}))
        body = request.call_args.kwargs['body']
        assert set(body) == {'alexandria','timeout'}
        assert body['alexandria'][0]['capability'] == 'catalog/search_catalog'


@pytest.mark.parametrize('price,per_record',[(6,False),(None,False),(5,True),(True,False)])
def test_unknown_or_variable_prices_are_denied(price,per_record,monkeypatch):
    monkeypatch.setenv('FIRECRAWL_API_KEY','test-only')
    data = {'success':True,'data':{'alexandria':[{'provider':'firecrawl','capability':'find-tools','data':{'items':[{'provider':'shopify','capability':'catalog/search_catalog','creditsCost':price,'perRecord':per_record}]}}]}}
    with patch.object(alexandria,'request',new_callable=AsyncMock,return_value=data):
        with pytest.raises(Denied):
            asyncio.run(alexandria.verify_price('shopify_search'))


@pytest.mark.parametrize('url',['http://example.com/','https://user:pass@example.com/','file:///etc/passwd'])
def test_tavily_extraction_denies_non_public_https_before_reservation(setup,url):
    _,_,ledger,mcp = setup
    with patch.object(tavily,'extract',new_callable=AsyncMock) as extract:
        with pytest.raises(SafeToolError):
            asyncio.run(mcp.tools['tavily_extract_pages']([url]))
        extract.assert_not_called()
        assert not ledger.calls


def test_tavily_extraction_reserves_one_and_never_upgrades(setup,monkeypatch):
    policy,config,ledger,mcp = setup
    monkeypatch.setenv('TAVILY_API_KEY','test-only')
    with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('93.184.216.34',443))]), patch.object(tavily,'request',new_callable=AsyncMock,return_value={'results':[{'url':'https://example.com/','raw_content':'hello'},{'url':'https://unapproved.test/','raw_content':'unexpected'}]}) as request:
        result = asyncio.run(mcp.tools['tavily_extract_pages'](['https://example.com/']))
        assert ledger.calls[0][2:4] == ('tavily',1)
        assert len(result['results']) == 1
        assert request.call_args.kwargs['body']['extract_depth'] == 'basic'
        assert request.call_args.kwargs['body']['timeout'] == 20


@pytest.mark.parametrize('address',['127.0.0.1','169.254.169.254','::1','fd00::1'])
def test_extraction_rejects_internal_address(setup,address):
    policy,config,ledger,mcp = setup
    with patch('socket.getaddrinfo',return_value=[(2,1,6,'',(address,443))]), patch.object(tavily,'extract',new_callable=AsyncMock) as extract:
        with pytest.raises(SafeToolError):
            asyncio.run(mcp.tools['tavily_extract_pages'](['https://example.com/']))
        extract.assert_not_called()
        assert not ledger.calls


@pytest.mark.parametrize('country,geo',[('MY','MY'),('GB','GB'),('WORLDWIDE','')])
def test_trends_accepts_any_iso_country_or_worldwide(setup,monkeypatch,country,geo):
    policy,config,ledger,mcp = setup
    monkeypatch.setenv('FIRECRAWL_API_KEY','test-only')
    with patch.object(alexandria,'verify_price',new_callable=AsyncMock), patch.object(alexandria,'execute',new_callable=AsyncMock,return_value={'series':[]}) as execute:
        asyncio.run(mcp.tools['firecrawl_trends'](['mugs'],country))
        assert execute.call_args.args[1]['geo'] == geo
        assert ledger.calls[0][2:4] == ('firecrawl',5)


@pytest.mark.parametrize('country',['sg','ZZ','SGP',''])
def test_unknown_country_codes_never_spend(setup,monkeypatch,country):
    policy,config,ledger,mcp = setup
    monkeypatch.setenv('FIRECRAWL_API_KEY','test-only')
    with patch.object(alexandria,'execute',new_callable=AsyncMock) as execute:
        with pytest.raises(SafeToolError):
            asyncio.run(mcp.tools['firecrawl_trends'](['mugs'],country))
        execute.assert_not_called()
        assert not ledger.calls


def test_explicit_country_list_still_limits_scope():
    policy = {'alexandria': {'countries': ['SG']}}
    with pytest.raises(Denied, match='outside shared access scope'):
        alexandria.country_check(policy, {'alexandria_countries': 'any'}, 'MY')
    assert alexandria.country_check(policy, {'alexandria_countries': ['SG']}, 'SG') == 'SG'
