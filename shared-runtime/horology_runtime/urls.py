"""Reusable HTTPS/public-address validation, independent of gateway policy.

This validates local DNS results. A remote fetch service can resolve differently
or follow redirects; callers must not treat this as control of that service's network.
"""
import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURL(ValueError):
    pass


def public_address(value):
    """Reject non-global, multicast and embedded non-public IPv4 addresses."""
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast or address.is_unspecified:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        embedded = [address.ipv4_mapped, address.sixtofour]
        if address.teredo:
            embedded.extend(address.teredo)
        if any(a is not None and not public_address(str(a)) for a in embedded):
            return False
    return True


def validate_public_https_url(url):
    """Allow a bounded HTTPS URL only when every locally resolved IP is public."""
    if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() or ord(c) < 32 for c in url) or '\\' in url:
        raise UnsafeURL('A bounded HTTPS URL without whitespace is required')
    try:
        parsed = urlsplit(url)
        port = 443 if parsed.port is None else parsed.port
        host = (parsed.hostname or '').rstrip('.').lower()
    except ValueError:
        raise UnsafeURL('Invalid HTTPS target') from None
    if parsed.scheme != 'https' or not host or parsed.username is not None or parsed.password is not None or parsed.fragment or not 1 <= port <= 65535 or '%' in host:
        raise UnsafeURL('Only public HTTPS URLs without credentials or fragments are supported')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise UnsafeURL('Local and internal target names are forbidden')
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and not public_address(str(literal)):
        raise UnsafeURL('Private and reserved target addresses are forbidden')
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        safe = bool(addresses) and all(public_address(record[4][0]) for record in addresses)
    except (socket.gaierror, ValueError, UnicodeError):
        raise UnsafeURL('Cannot verify public target address') from None
    if not safe:
        raise UnsafeURL('Private and reserved target addresses are forbidden')
