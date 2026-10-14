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
LLM_MODEL = os.environ.get("GRAPH_LLM_MODEL", "google/gemini-3.1-flash-lite")
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


@observe("openrouter")
async def complete_json(system: str, user: str, schema_name: str, schema: dict) -> dict:
    """Ask the model for one JSON object matching schema (strict structured output)."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in this server's environment.")
    body = {
        "model": LLM_MODEL,
        "temperature": 0,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": for_provider(user)}],
        "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
    }
    async with httpx.AsyncClient(timeout=TIMEOUTS.openrouter_http) as http:
        resp = await http.post(OPENROUTER_CHAT_URL, headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}, json=body)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("Model reply is not a JSON object")
    return data
