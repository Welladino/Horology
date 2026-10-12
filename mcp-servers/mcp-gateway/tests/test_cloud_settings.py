"""Local/cloud transport configuration; no provider or cloud calls."""
import pytest
from horology_runtime.settings import http_server_options, gateway_public_url


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for key in ('PORT', 'K_SERVICE', 'GATEWAY_BIND', 'GATEWAY_PUBLIC_URL'):
        monkeypatch.delenv(key, raising=False)


def test_local_defaults_and_stateless_transport():
    assert http_server_options(8767, 'GATEWAY_BIND', '127.0.0.1') == {
        'host': '127.0.0.1', 'port': 8767, 'stateless_http': True, 'json_response': True}
    assert gateway_public_url() == 'http://localhost:8767'


def test_cloud_run_port_and_public_auth_url(monkeypatch):
    monkeypatch.setenv('K_SERVICE', 'mcp-gateway')
    monkeypatch.setenv('PORT', '8080')
    monkeypatch.setenv('GATEWAY_PUBLIC_URL', 'https://gateway.example.com/')
    options = http_server_options(8767, 'GATEWAY_BIND', '127.0.0.1')
    assert (options['host'], options['port']) == ('0.0.0.0', 8080)
    assert gateway_public_url() == 'https://gateway.example.com'


@pytest.mark.parametrize('value', ['0', '65536', 'invalid'])
def test_invalid_ports_fail_startup(monkeypatch, value):
    monkeypatch.setenv('PORT', value)
    with pytest.raises(ValueError):
        http_server_options(8767, 'GATEWAY_BIND', '127.0.0.1')


@pytest.mark.parametrize('value', ['http://remote.example.com', 'https://user:password@example.com', 'https://example.com/mcp', 'https://example.com?token=secret'])
def test_unsafe_auth_base_urls_fail_startup(monkeypatch, value):
    monkeypatch.setenv('GATEWAY_PUBLIC_URL', value)
    with pytest.raises(ValueError):
        gateway_public_url()
