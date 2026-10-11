"""OpenRouter embedding requests; no database access."""
import os
from horology_runtime.settings import TIMEOUTS
import httpx
from horology_runtime.operations import observe

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "google/gemini-embedding-001")
OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
EMBED_DIMENSIONS = 768

@observe("openrouter")
def _embed(text: str) -> list[float]:
    """Embed text via OpenRouter's OpenAI-compatible /v1/embeddings endpoint.
    Raises if OPENROUTER_API_KEY is unset or the request fails - callers
    should let this propagate as a tool error rather than silently skip
    auto-linking.

    `dimensions` is undocumented on OpenRouter's embeddings endpoint but
    verified working live (passed through to Gemini's native
    output_dimensionality) - the model's un-truncated output is 3072 dims,
    which exceeds pgvector's 2000-dim HNSW index limit, so this is required,
    not optional."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in this server's environment.")
    resp = httpx.post(
        OPENROUTER_EMBEDDINGS_URL,
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={"model": EMBED_MODEL, "input": text, "dimensions": EMBED_DIMENSIONS},
        timeout=TIMEOUTS.openrouter_http,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]
