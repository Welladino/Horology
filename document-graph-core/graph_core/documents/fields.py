"""Document fields copied from the Document Index, each kept in one stored form.

The registers spell domains differently ("Welladino" in the Pipeline,
"welladino" in the Document Index), so the graph stores a normal form and
filters accept either spelling.
"""
import re

_NOT_SLUG = re.compile(r"[^a-z0-9]+")


def domain(value):
    """'Article Aggregator' -> 'article-aggregator'; blank -> None."""
    slug = _NOT_SLUG.sub("-", str(value or "").strip().lower()).strip("-")
    return slug or None


def business_entity(value):
    text = str(value or "").strip()
    return text or None


def pipeline_id(value):
    """Permanent numeric Pipeline ID as text ('12', from 12, 12.0 or ' 12 '); blank -> None."""
    if value is None or value == "":
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if not text:
        return None
    if not text.isdigit():
        raise ValueError(f"Pipeline ID must be a number, got {value!r}")
    return str(int(text))
