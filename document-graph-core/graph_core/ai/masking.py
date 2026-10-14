"""Mask what outside providers must not receive; the stored text is never changed.

OpenRouter's content filter rejects requests containing IP addresses (403
"blocked by content filter: [IP_ADDRESS]", seen 2026-10-14), and internal
addresses shouldn't leave our systems anyway. Masking them doesn't change
what a passage means for search, topics or naming.
"""
import re

IP_PLACEHOLDER = "[ip address]"
_IPV4 = re.compile(r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?!\w|\.\d)")
# Needs '::' or a hex letter, so clock times like 14:21:50 are left alone. It may be followed by a
# punctuation colon ("fe80::1: refused"), but not by another address part.
_IPV6 = re.compile(r"(?<![\w:])(?=[0-9A-Fa-f:]*(?:::|[A-Fa-f]))(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}"
                   r"(?!\w|:[0-9A-Fa-f:])")


def for_provider(text):
    return _IPV6.sub(IP_PLACEHOLDER, _IPV4.sub(IP_PLACEHOLDER, text))
