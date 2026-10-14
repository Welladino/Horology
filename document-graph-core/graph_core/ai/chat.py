"""JSON chat for the graph. The backend is a setting (GRAPH_AI_BACKEND, default openrouter);
IP addresses are masked before text leaves."""
import os

from .gate import gate
from .masking import for_provider
from .openrouter import chat as openrouter

BACKENDS = {"openrouter": openrouter}
BACKEND = os.environ.get("GRAPH_AI_BACKEND", "openrouter")
if BACKEND not in BACKENDS:
    raise RuntimeError(f"Unknown GRAPH_AI_BACKEND {BACKEND!r}; known: {', '.join(BACKENDS)}")

MODEL = os.environ.get("GRAPH_LLM_MODEL", "google/gemini-2.5-flash-lite")
# Deciding whether two names are the same thing needs a stronger model: Flash Lite merged
# "Newsletter" into "Article Aggregator" with 0.8 confidence in the 2026-10-14 trial.
JUDGE_MODEL = os.environ.get("GRAPH_JUDGE_MODEL", "google/gemini-2.5-flash")
MAX_TOKENS = 4096  # caps cost and time if the model loops (seen 2026-10-14: a 65,535-token runaway)


async def complete_json(system: str, user: str, schema_name: str, schema: dict, max_tokens: int = MAX_TOKENS,
                        model: str | None = None) -> dict | None:
    """Ask the model for one JSON object matching schema (strict structured output).

    Returns None when the reply was cut off at max_tokens (the model can loop
    on long lists), so the caller can retry with less input."""
    async with gate():
        return await BACKENDS[BACKEND].complete_json(system, for_provider(user), schema_name, schema, max_tokens,
                                                     model or MODEL)
