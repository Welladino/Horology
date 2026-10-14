"""OpenRouter embeddings (768 dimensions); no database access."""
import os
from horology_runtime.settings import TIMEOUTS
import httpx
from horology_runtime.operations import observe

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "google/gemini-embedding-001")
OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
EMBED_DIMENSIONS = 768

BATCH = 32  # sections per request; OpenRouter returns one embedding per input, by index


async def embed(text: str) -> list[float]:
    """Embed one text (a search query or a single section)."""
    return (await embed_many([text]))[0]


@observe("openrouter")
async def embed_many(texts: list[str]) -> list[list[float]]:
    """Embed texts via OpenRouter's OpenAI-compatible /v1/embeddings endpoint,
    BATCH inputs per request, returned in input order.
    Raises if OPENROUTER_API_KEY is unset or a request fails - callers
    should let this propagate as a tool error rather than silently skip
    auto-linking.

    `dimensions` is undocumented on OpenRouter's embeddings endpoint but
    verified working live (passed through to Gemini's native
    output_dimensionality) - the model's un-truncated output is 3072 dims,
    which exceeds pgvector's 2000-dim HNSW index limit, so this is required,
    not optional. Batched input verified live on 2026-10-14."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in this server's environment.")
    vectors = []
    async with httpx.AsyncClient(timeout=TIMEOUTS.openrouter_http) as http:
        for start in range(0, len(texts), BATCH):
            batch = texts[start:start + BATCH]
            resp = await http.post(
                OPENROUTER_EMBEDDINGS_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                json={"model": EMBED_MODEL, "input": batch, "dimensions": EMBED_DIMENSIONS},
            )
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda item: item.get("index", 0))
            if len(data) != len(batch):
                raise RuntimeError("Embedding response does not match the request")
            vectors.extend(item["embedding"] for item in data)
    return vectors
