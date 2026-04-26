from __future__ import annotations

from abc import ABC, abstractmethod
import os
import time
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError


class LLMClientError(RuntimeError):
    pass


class MissingAPIKeyError(LLMClientError):
    pass


class LLMProviderError(LLMClientError):
    pass


class LLMClient(ABC):
    @abstractmethod
    def analyze_requirement(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAIClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "gpt-4.1-mini",
        max_output_tokens: int = 2000,
        temperature: float = 0.1,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ):
        load_dotenv()

        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise MissingAPIKeyError(
                "Missing OPENAI_API_KEY. Add it to your environment or to a .env file."
            )

        self._client = OpenAI(api_key=resolved_key, timeout=timeout_seconds)
        self._model = os.getenv("OPENAI_MODEL", model)
        self._max_output_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(max_output_tokens)))
        self._temperature = float(os.getenv("OPENAI_TEMPERATURE", str(temperature)))
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def analyze_requirement(self, prompt: str) -> str:
        last_err: Optional[BaseException] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a senior QA manager, product delivery lead, "
                                "and risk-aware stakeholder reviewer."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self._temperature,
                    max_tokens=self._max_output_tokens,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                if content is None:
                    raise LLMProviderError("OpenAI returned an empty response.")
                return content

            except (RateLimitError, APITimeoutError, APIConnectionError) as e:
                last_err = e
            except APIError as e:
                # Retry server-side failures; do not retry clear client-side input errors.
                last_err = e
                status = getattr(e, "status_code", None)
                if status is not None and 400 <= int(status) < 500 and int(status) != 429:
                    break
            except Exception as e:  # noqa: BLE001
                # Unknown failure; do not leak secrets.
                raise LLMProviderError(f"LLM request failed: {e.__class__.__name__}: {e}") from e

            if attempt < self._max_retries:
                # Basic exponential backoff with small cap.
                sleep_s = min(8.0, 0.75 * (2 ** (attempt - 1)))
                time.sleep(sleep_s)

        msg = (
            f"OpenAI request failed after {self._max_retries} attempt(s). "
            f"Last error: {last_err.__class__.__name__ if last_err else 'UnknownError'}"
        )
        raise LLMProviderError(msg)


class AnthropicClient(LLMClient):
    def __init__(self):
        raise NotImplementedError("Anthropic client not yet implemented")

    def analyze_requirement(self, prompt: str) -> str:
        raise NotImplementedError("Anthropic client not yet implemented")


def get_llm_client(provider: str = "openai") -> LLMClient:
    provider_normalized = provider.strip().lower()
    if provider_normalized == "openai":
        return OpenAIClient()
    if provider_normalized in {"anthropic", "claude"}:
        return AnthropicClient()
    raise ValueError(f"Unknown LLM provider: {provider}")


def analyze_requirement(prompt: str, *, provider: str = "openai") -> str:
    client = get_llm_client(provider=provider)
    return client.analyze_requirement(prompt)
