"""Rules that must hold for any text, checked on generated inputs (Hypothesis): masking and chunking."""
import ipaddress
import re

from hypothesis import given, settings, strategies as st

from graph_core.ai.masking import IP_PLACEHOLDER, for_provider
from graph_core.sections import chunking

SEPARATORS = st.sampled_from([" ", "\n", ", ", "; ", " (", ") ", "[", "] ", "\t", ": "])
WORDS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=12)
PROSE = st.lists(WORDS, max_size=20).map(" ".join)
IPV4 = st.ip_addresses(v=4).map(str)
# Addresses the masker covers by design: with '::' or a hex letter, so clock times like 14:21:50 stay.
IPV6 = st.ip_addresses(v=6).map(str).filter(lambda a: "::" in a or re.search(r"[a-f]", a))
QUAD = re.compile(r"(?<![\w.])(\d{1,3}\.){3}\d{1,3}(?![\w.])")


@settings(max_examples=300, deadline=None)
@given(st.lists(st.tuples(PROSE, SEPARATORS, st.one_of(IPV4, IPV6), SEPARATORS), min_size=1, max_size=5))
def test_no_ip_address_survives_masking(parts):
    text = "".join(f"{prose}{before}{address}{after}" for prose, before, address, after in parts)
    masked = for_provider(text)
    for _, _, address, _ in parts:
        assert address not in masked.split() and address not in re.split(r"[\s,;()\[\]]+", masked)
    assert not any(ipaddress.ip_address(m.group(0).strip()) for m in QUAD.finditer(masked)
                   if _is_ipv4(m.group(0)))
    assert masked.count(IP_PLACEHOLDER) >= len(parts)


def _is_ipv4(value):
    try:
        ipaddress.IPv4Address(value.strip())
        return True
    except ValueError:
        return False


@settings(max_examples=300, deadline=None)
@given(st.text(alphabet=st.characters(blacklist_categories=("Nd",)), max_size=300))
def test_text_without_digits_is_unchanged(text):
    assert for_provider(text) == text


@given(st.integers(0, 23), st.integers(0, 59), st.integers(0, 59), st.integers(0, 99), st.integers(0, 99))
def test_times_and_version_numbers_are_left_alone(hour, minute, second, major, minor):
    text = f"At {hour:02d}:{minute:02d}:{second:02d} we shipped v{major}.{minor}.{second} and 2.{minor}."
    assert for_provider(text) == text


PARAGRAPHS = st.lists(
    st.one_of(st.lists(WORDS, min_size=1, max_size=600).map(lambda w: " ".join(w) + "."),  # up to ~7k chars
              WORDS.map(lambda w: f"# {w}")),
    max_size=25)


@settings(max_examples=200, deadline=None)
@given(PARAGRAPHS)
def test_sections_stay_under_the_limit_and_keep_every_word_in_order(paragraphs):
    text = "\n\n".join(paragraphs)
    sections = chunking.split(text)
    assert all(0 < len(s) <= chunking.MAX_CHARS for s in sections)
    # Every word appears, and in order, once the overlap repeated at the start of a section is skipped.
    words, position = text.split(), 0
    joined = " ".join(sections).split()
    for word in words:
        position = joined.index(word, position) + 1
    assert chunking.split(text) == sections  # deterministic


@given(st.text(alphabet=" \n\t\r", max_size=50))
def test_blank_text_has_no_sections(text):
    assert chunking.split(text) == []
