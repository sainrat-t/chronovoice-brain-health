"""Tests for the model clients, against stand-ins for the vendor SDK clients."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest
from mistralai.client import errors as mistral_errors
from pydantic import BaseModel

from app.llm import LLMError, create_llm_client
from app.llm.claude import EFFORT, FALLBACK_BETA, MODEL, ClaudeClient
from app.llm.mistral import DEFAULT_MODEL, MistralClient


class Answer(BaseModel):
    text: str


class _Messages:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _client(result: Any) -> tuple[ClaudeClient, _Messages]:
    messages = _Messages(result)
    sdk = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return ClaudeClient(client=sdk), messages  # type: ignore[arg-type]


def _response(**overrides: Any) -> SimpleNamespace:
    fields = {"stop_reason": "end_turn", "parsed_output": Answer(text="ok"), "model": MODEL}
    return SimpleNamespace(**(fields | overrides))


def _status_error(cls: type[anthropic.APIStatusError], status: int) -> anthropic.APIStatusError:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("error", response=httpx2.Response(status, request=request), body=None)


def test_request_uses_the_chosen_model_structured_output_and_fallbacks() -> None:
    client, messages = _client(_response())

    reply = client.generate(system="You summarise.", user="The facts.", output=Answer)

    assert (reply.output, reply.model_id) == (Answer(text="ok"), MODEL)
    sent = messages.kwargs
    assert sent["model"] == MODEL == "claude-opus-5-5"
    assert sent["system"] == "You summarise."
    assert sent["messages"] == [{"role": "user", "content": "The facts."}]
    assert sent["output_format"] is Answer
    assert sent["output_config"] == {"effort": EFFORT}
    assert (sent["betas"], sent["fallbacks"]) == ([FALLBACK_BETA], "default")
    # No sampling or thinking parameter: the model rejects them or runs adaptive thinking.
    assert {"temperature", "top_p", "thinking"}.isdisjoint(sent)


def test_model_that_actually_answered_is_reported() -> None:
    client, _ = _client(_response(model="claude-opus-5"))

    assert client.generate(system="s", user="u", output=Answer).model_id == "claude-opus-5"


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_refusal_or_truncated_answer_is_an_error(stop_reason: str) -> None:
    client, _ = _client(_response(stop_reason=stop_reason))

    with pytest.raises(LLMError, match=stop_reason):
        client.generate(system="s", user="u", output=Answer)


def test_missing_structured_output_is_an_error() -> None:
    client, _ = _client(_response(parsed_output=None))

    with pytest.raises(LLMError, match="no structured output"):
        client.generate(system="s", user="u", output=Answer)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (_status_error(anthropic.AuthenticationError, 401), "credentials"),
        (_status_error(anthropic.RateLimitError, 429), "rate limit"),
        (_status_error(anthropic.InternalServerError, 500), "status 500"),
        (
            anthropic.APIConnectionError(
                request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
            ),
            "could not be reached",
        ),
    ],
)
def test_api_failures_become_llm_errors(error: Exception, message: str) -> None:
    client, _ = _client(error)

    with pytest.raises(LLMError, match=message):
        client.generate(system="s", user="u", output=Answer)


# --- Mistral ----------------------------------------------------------------


class _Chat:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _mistral(result: Any) -> tuple[MistralClient, _Chat]:
    chat = _Chat(result)
    return MistralClient(client=SimpleNamespace(chat=chat)), chat  # type: ignore[arg-type]


OK = Answer(text="ok")


def _mistral_response(
    finish_reason: str = "stop", parsed: Any = OK, model: str = "mistral-small-2603"
) -> SimpleNamespace:
    message = SimpleNamespace(parsed=parsed)
    return SimpleNamespace(
        model=model, choices=[SimpleNamespace(finish_reason=finish_reason, message=message)]
    )


def test_mistral_request_uses_the_small_model_and_a_structured_output() -> None:
    client, chat = _mistral(_mistral_response())

    reply = client.generate(system="You summarise.", user="The facts.", output=Answer)

    assert reply.output == Answer(text="ok")
    # The model that answered, as reported by the API, not the alias that was asked for.
    assert reply.model_id == "mistral-small-2603"
    sent = chat.kwargs
    assert sent["model"] == DEFAULT_MODEL == "mistral-small-latest"
    assert sent["messages"] == [
        {"role": "system", "content": "You summarise."},
        {"role": "user", "content": "The facts."},
    ]
    assert sent["response_format"] is Answer
    # Both are needed: Mistral Large refuses temperature 0 unless top_p is 1.
    assert (sent["temperature"], sent["top_p"]) == (0, 1)
    # Not every model accepts a reasoning effort: it is sent only when configured.
    assert "reasoning_effort" not in sent


def test_mistral_reasoning_effort_is_sent_when_configured() -> None:
    chat = _Chat(_mistral_response())
    client = MistralClient(client=SimpleNamespace(chat=chat), reasoning_effort="high")  # type: ignore[arg-type]

    client.generate(system="s", user="u", output=Answer)

    assert chat.kwargs["reasoning_effort"] == "high"


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (_mistral_response(finish_reason="length"), "length"),
        (SimpleNamespace(model="m", choices=[]), "no answer"),
        (_mistral_response(parsed=None), "no structured output"),
    ],
)
def test_mistral_truncated_or_empty_answer_is_an_error(response: Any, message: str) -> None:
    client, _ = _mistral(response)

    with pytest.raises(LLMError, match=message):
        client.generate(system="s", user="u", output=Answer)


def _invalid_answer() -> Exception:
    try:
        Answer.model_validate({"text": 3})
    except ValueError as error:
        return error
    raise AssertionError("expected a validation error")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            mistral_errors.SDKError(
                "error",
                httpx2.Response(429, request=httpx2.Request("POST", "https://api.mistral.ai/v1")),
            ),
            "status 429",
        ),
        (mistral_errors.NoResponseError("no response"), "could not be reached"),
        (httpx2.ConnectError("connection refused"), "could not be reached"),
        (_invalid_answer(), "outside the expected format"),
    ],
)
def test_mistral_failures_become_llm_errors(error: Exception, message: str) -> None:
    client, _ = _mistral(error)

    with pytest.raises(LLMError, match=message):
        client.generate(system="s", user="u", output=Answer)


# --- Choice of the provider -------------------------------------------------


def test_no_key_means_no_model() -> None:
    assert create_llm_client({}) is None


def test_the_provider_whose_key_is_present_is_used() -> None:
    mistral = create_llm_client({"MISTRAL_API_KEY": "test-key"})
    claude = create_llm_client({"ANTHROPIC_API_KEY": "test-key"})

    assert isinstance(mistral, MistralClient)
    assert mistral._model == DEFAULT_MODEL
    assert isinstance(claude, ClaudeClient)


def test_mistral_model_and_reasoning_can_be_changed_by_configuration() -> None:
    client = create_llm_client(
        {
            "MISTRAL_API_KEY": "test-key",
            "MISTRAL_MODEL": "mistral-large-latest",
            "MISTRAL_REASONING_EFFORT": "low",
        }
    )

    assert isinstance(client, MistralClient)
    assert client._model == "mistral-large-latest"
    assert client._reasoning == {"reasoning_effort": "low"}
    default = create_llm_client({"MISTRAL_API_KEY": "test-key"})
    assert isinstance(default, MistralClient)
    assert default._reasoning == {}


def test_llm_provider_decides_when_both_keys_are_present() -> None:
    both = {"MISTRAL_API_KEY": "test-key", "ANTHROPIC_API_KEY": "test-key"}

    assert isinstance(create_llm_client(both), ClaudeClient)
    assert isinstance(create_llm_client(both | {"LLM_PROVIDER": "mistral"}), MistralClient)
    assert isinstance(create_llm_client(both | {"LLM_PROVIDER": "Anthropic"}), ClaudeClient)


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"LLM_PROVIDER": "mistral"}, "MISTRAL_API_KEY is not set"),
        ({"LLM_PROVIDER": "anthropic"}, "ANTHROPIC_API_KEY is not set"),
        ({"LLM_PROVIDER": "openai", "MISTRAL_API_KEY": "test-key"}, "unknown LLM_PROVIDER"),
    ],
)
def test_inconsistent_configuration_is_refused(env: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        create_llm_client(env)
