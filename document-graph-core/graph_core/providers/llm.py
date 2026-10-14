"""OpenRouter chat completions that must answer in a given JSON schema; no database access.

Used for naming topics and, later, extracting and resolving entities. The
model is a setting so it can change without code changes.
"""
import json
import os

import httpx
from horology_runtime.operations import observe
from horology_runtime.settings import TIMEOUTS

from .masking import for_provider

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
LLM_MODEL = os.environ.get("GRAPH_LLM_MODEL", "google/gemini-2.5-flash-lite")
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_TOKENS = 4096  # caps cost and time if the model loops (seen 2026-10-14: a 65,535-token runaway)


@observe("openrouter")
async def complete_json(system: str, user: str, schema_name: str, schema: dict, max_tokens: int = MAX_TOKENS) -> dict | None:
    """Ask the model for one JSON object matching schema (strict structured output).

    Returns None when the reply was cut off at max_tokens (the model can loop
    on long lists), so the caller can retry with less input."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in this server's environment.")
    body = {
        "model": LLM_MODEL,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": for_provider(user)}],
        "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
    }
    async with httpx.AsyncClient(timeout=TIMEOUTS.openrouter_http) as http:
        resp = await http.post(OPENROUTER_CHAT_URL, headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}, json=body)
    resp.raise_for_status()
    choice = resp.json()["choices"][0]
    if choice.get("finish_reason") == "length":
        return None
    content = choice["message"]["content"]
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("Model reply is not a JSON object")
    return data
