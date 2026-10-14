"""The public-URL check (horology_runtime.urls) on generated addresses (Hypothesis).

Only IP literals are generated, so no DNS lookups are made."""
import ipaddress

import pytest
from hypothesis import assume, given, settings, strategies as st

from horology_runtime.urls import UnsafeURL, public_address, validate_public_https_url

PRIVATE_V4 = st.one_of(*[st.ip_addresses(network=n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16", "100.64.0.0/10", "0.0.0.0/8",
    "224.0.0.0/4", "240.0.0.0/4")])
PRIVATE_V6 = st.one_of(*[st.ip_addresses(network=n) for n in ("::1/128", "fc00::/7", "fe80::/10", "ff00::/8")])


def url(address, path="/x"):
    host = f"[{address}]" if isinstance(address, ipaddress.IPv6Address) else str(address)
    return f"https://{host}{path}"


@settings(max_examples=300)
@given(st.one_of(PRIVATE_V4, PRIVATE_V6))
def test_private_and_reserved_addresses_are_refused(address):
    with pytest.raises(UnsafeURL):
        validate_public_https_url(url(address))


@settings(max_examples=300)
@given(PRIVATE_V4)
def test_private_ipv4_hidden_in_an_ipv6_address_is_refused(address):
    for wrapped in (ipaddress.IPv6Address(f"::ffff:{address}"),  # IPv4-mapped
                    ipaddress.IPv6Address((0x2002 << 112) | (int(address) << 80))):  # 6to4
        assert not public_address(str(wrapped))


@settings(max_examples=200)
@given(st.ip_addresses(v=4))
def test_public_ipv4_literals_are_allowed(address):
    assume(address.is_global and not address.is_multicast)
    validate_public_https_url(url(address))  # a literal needs no DNS lookup


@given(st.ip_addresses(v=4), st.sampled_from(["http", "ftp", "file", "gopher", "ws"]))
def test_only_https_is_allowed(address, scheme):
    with pytest.raises(UnsafeURL):
        validate_public_https_url(f"{scheme}://{address}/x")


@given(st.text(alphabet="abc:@", min_size=1, max_size=10))
def test_credentials_in_the_url_are_refused(userinfo):
    assume("@" not in userinfo)
    with pytest.raises(UnsafeURL):
        validate_public_https_url(f"https://{userinfo}@93.184.216.34/x")
