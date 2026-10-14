"""Retries for AI requests, and the OpenRouter backends using them. No network."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from graph_core.ai import chat, retry
from graph_core.ai.openrouter import chat as openrouter_chat


def status_error(status, headers=None):
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(status, headers=headers or {}, request=request)
    return httpx.HTTPStatusError(f"{status}", request=request, response=response)


def attempts(*outcomes):
    """A request that raises or returns each outcome in turn, and counts its calls."""
    calls = []

    async def request():
        outcome = outcomes[len(calls)]
        calls.append(outcome)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    return request, calls


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.fixture
def waits():
    sleeper = AsyncMock()
    with patch.object(retry, "sleep", sleeper):
        yield sleeper


@pytest.mark.parametrize("error", [httpx.ReadTimeout("slow"), httpx.ConnectError("down"), status_error(429),
                                   status_error(500), status_error(503)])
def test_passing_failures_are_retried(waits, error, caplog):
    request, calls = attempts(error, "ok")
    assert run(retry.call(request)) == "ok"
    assert len(calls) == 2 and waits.await_count == 1
    expected = "timeout" if isinstance(error, httpx.TimeoutException) else (
        "provider_rejected" if isinstance(error, httpx.HTTPStatusError) else "connection_failed")
    assert f"retry 1 of 2 after {expected}" in caplog.text


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_other_failures_are_raised_at_once(waits, status):
    # 403 includes OpenRouter's content filter: the same text is blocked again.
    request, calls = attempts(status_error(status), "ok")
    with pytest.raises(httpx.HTTPStatusError):
        run(retry.call(request))
    assert len(calls) == 1 and waits.await_count == 0


def test_gives_up_after_three_attempts(waits):
    request, calls = attempts(*[httpx.ReadTimeout("slow")] * 3)
    with pytest.raises(httpx.ReadTimeout):
        run(retry.call(request))
    assert len(calls) == 3
    first, second = (call.args[0] for call in waits.await_args_list)
    assert 1 <= first <= 1.5 and 3 <= second <= 3.5


def test_retry_after_is_honoured_and_capped(waits):
    request, _ = attempts(status_error(429, {"retry-after": "7"}), status_error(429, {"retry-after": "600"}), "ok")
    assert run(retry.call(request)) == "ok"
    assert [call.args[0] for call in waits.await_args_list] == [7, retry.MAX_RETRY_AFTER]


def test_chat_masks_retries_and_uses_the_default_model(waits, monkeypatch):
    monkeypatch.setattr(openrouter_chat, "OPENROUTER_API_KEY", "sk-or-fake-key")
    response = MagicMock()
    response.json.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": '{"name": "x"}'}}]}
    post = AsyncMock(side_effect=[httpx.ReadTimeout("slow"), response])
    with patch.object(openrouter_chat.httpx.AsyncClient, "post", post):
        reply = run(chat.complete_json("system", "server 10.0.0.1", "topic_name", {"type": "object"}))
    assert reply == {"name": "x"} and post.await_count == 2
    body = post.call_args.kwargs["json"]
    assert body["model"] == chat.MODEL and body["messages"][1]["content"] == "server [ip address]"


def test_chat_returns_none_when_the_reply_is_cut_off(waits, monkeypatch):
    monkeypatch.setattr(openrouter_chat, "OPENROUTER_API_KEY", "sk-or-fake-key")
    response = MagicMock()
    response.json.return_value = {"choices": [{"finish_reason": "length", "message": {"content": '{"na'}}]}
    with patch.object(openrouter_chat.httpx.AsyncClient, "post", AsyncMock(return_value=response)):
        assert run(chat.complete_json("s", "u", "n", {}, model=chat.JUDGE_MODEL)) is None


@pytest.mark.parametrize("content", ["[]", "not json"])  # a list, not an object; not JSON at all
def test_a_reply_in_the_wrong_shape_is_a_provider_response_error(waits, monkeypatch, content):
    from horology_runtime.error_handling import SafeToolError
    monkeypatch.setattr(openrouter_chat, "OPENROUTER_API_KEY", "sk-or-fake-key")
    response = MagicMock()
    response.json.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
    with patch.object(openrouter_chat.httpx.AsyncClient, "post", AsyncMock(return_value=response)):
        with pytest.raises(SafeToolError) as raised:
            run(chat.complete_json("s", "u", "n", {}))
    assert raised.value.category == "invalid_provider_response"
