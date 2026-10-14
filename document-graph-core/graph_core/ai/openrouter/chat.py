"""OpenRouter chat completions that must answer in a given JSON schema."""
import json
import os

import httpx
from horology_runtime.error_handling import ProviderResponseError
from horology_runtime.operations import observe
from horology_runtime.settings import TIMEOUTS

from .. import retry

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


@observe("openrouter")
async def complete_json(system, user, schema_name, schema, max_tokens, model):
    """One JSON object matching schema (strict structured output), or None if the reply was cut off."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in this server's environment.")
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
    }

    async def request():
        async with httpx.AsyncClient(timeout=TIMEOUTS.openrouter_chat_http) as http:
            resp = await http.post(OPENROUTER_CHAT_URL, headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}, json=body)
        resp.raise_for_status()
        return resp.json()

    choice = (await retry.call(request))["choices"][0]
    if choice.get("finish_reason") == "length":
        return None
    data = json.loads(choice["message"]["content"])
    if not isinstance(data, dict):
        raise ProviderResponseError("Model reply is not a JSON object")
    return data
