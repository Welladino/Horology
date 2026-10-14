"""IP addresses are masked before text goes to an outside provider."""
import pytest

from graph_core.providers.masking import for_provider


@pytest.mark.parametrize("text,expected", [
    ("bind 127.0.0.1:8765 and 10.0.0.12", "bind [ip address]:8765 and [ip address]"),
    ("server ip 34.143.78.2.", "server ip [ip address]."),
    ("IPv6 ::1 and fd00::1 and 2001:db8::8a2e:370:7334", "IPv6 [ip address] and [ip address] and [ip address]"),
])
def test_ip_addresses_are_masked(text, expected):
    assert for_provider(text) == expected


@pytest.mark.parametrize("text", ["psycopg 3.3.6", "at 14:21:50 UTC", "version 1.2.3.4.5", "300.1.1.1", "ratio 1:2:3"])
def test_versions_times_and_lookalikes_are_left_alone(text):
    assert for_provider(text) == text
