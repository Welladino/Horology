"""Split document text into sections for passage search.

Sections hold whole paragraphs where possible, up to MAX_CHARS. A Markdown
heading starts a new section once the current one is reasonably full; a
section that had to continue past the limit repeats the previous section's
last ~OVERLAP characters so a sentence spanning the cut stays findable.
"""
import re

MAX_CHARS = 2000
MIN_BEFORE_HEADING = 900
OVERLAP = 200
MAX_SECTIONS = 30  # about 20 pages; longer documents are rejected whole, never cut short

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_HEADING = re.compile(r"#{1,6}\s")


class TooLong(ValueError):
    """A document with more than MAX_SECTIONS sections; nothing of it is stored or sent to a provider."""

    def __init__(self, sections):
        self.sections = sections
        super().__init__(f"Document has {sections} sections; the limit is {MAX_SECTIONS} (about 20 pages)")


def split(text):
    """Return the document's sections in order; [] for empty text."""
    pieces = []
    for block in _PARAGRAPH_BREAK.split(text.replace("\r\n", "\n").strip()):
        block = block.strip()
        while len(block) > MAX_CHARS:
            cut = _cut_point(block, MAX_CHARS)
            pieces.append(block[:cut].strip())
            block = block[cut:].strip()
        if block:
            pieces.append(block)

    sections, current = [], ""
    for piece in pieces:
        heading = bool(_HEADING.match(piece))
        if current and heading and len(current) >= MIN_BEFORE_HEADING:
            sections.append(current)
            current = ""  # a new heading is a clean start: no overlap
        elif current and len(current) + 2 + len(piece) > MAX_CHARS:
            sections.append(current)
            tail = _tail(current)
            current = tail if len(tail) + 2 + len(piece) <= MAX_CHARS else ""
        current = current + "\n\n" + piece if current else piece
    if current:
        sections.append(current)
    return sections


def _cut_point(text, limit):
    """Last sentence end, else last line break or space, before limit."""
    window = text[:limit]
    for pattern in (r"[.!?]\s", r"\n", r"\s"):
        ends = [m.end() for m in re.finditer(pattern, window)]
        if ends and ends[-1] > limit // 2:
            return ends[-1]
    return limit


def _tail(text):
    tail = text[-OVERLAP:]
    space = tail.find(" ")
    return tail[space + 1:] if 0 <= space < len(tail) - 1 else tail
