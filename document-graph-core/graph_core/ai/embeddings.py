"""Embeddings for the graph (768 dimensions, to match the database). The backend is a setting
(GRAPH_AI_BACKEND, default openrouter); IP addresses are masked before text leaves."""
import os

from .masking import for_provider
from .openrouter import embeddings as openrouter

BACKENDS = {"openrouter": openrouter}
BACKEND = os.environ.get("GRAPH_AI_BACKEND", "openrouter")
if BACKEND not in BACKENDS:
    raise RuntimeError(f"Unknown GRAPH_AI_BACKEND {BACKEND!r}; known: {', '.join(BACKENDS)}")

EMBED_MODEL = os.environ.get("EMBED_MODEL", "google/gemini-embedding-001")
EMBED_DIMENSIONS = 768


async def embed(text: str) -> list[float]:
    """Embed one text (a search query or a single section)."""
    return (await embed_many([text]))[0]


async def embed_many(texts: list[str]) -> list[list[float]]:
    """Embeddings in input order. Raises if a request still fails after retries; callers let
    that propagate as a tool error rather than silently skip auto-linking."""
    return await BACKENDS[BACKEND].embed_many([for_provider(text) for text in texts], EMBED_MODEL, EMBED_DIMENSIONS)
