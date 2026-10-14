"""OpenRouter embeddings through its OpenAI-compatible /v1/embeddings endpoint."""
import os

import httpx
from horology_runtime.error_handling import ProviderResponseError
from horology_runtime.operations import observe
from horology_runtime.settings import TIMEOUTS

from .. import retry

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
BATCH = 32  # inputs per request; OpenRouter returns one embedding per input, by index


@observe("openrouter")
async def embed_many(texts, model, dimensions):
    """Embeddings in input order, BATCH inputs per request; each request is retried on its own.

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

            async def request():
                resp = await http.post(OPENROUTER_EMBEDDINGS_URL, headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                                       json={"model": model, "input": batch, "dimensions": dimensions})
                resp.raise_for_status()
                return resp.json()

            data = sorted((await retry.call(request))["data"], key=lambda item: item.get("index", 0))
            if len(data) != len(batch):
                raise ProviderResponseError("Embedding response does not match the request")
            vectors.extend(item["embedding"] for item in data)
    return vectors
