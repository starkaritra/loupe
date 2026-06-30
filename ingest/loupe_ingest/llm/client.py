"""Public LLM interface re-exports + a MockClient for offline, $0 testing."""
from __future__ import annotations

from typing import Callable, Optional

from .providers import (
    AnthropicClient,
    GeminiClient,
    LLMClient,
    LLMResponse,
    OllamaClient,
    OpenAIClient,
    make_client,
)


class MockClient(LLMClient):
    """Deterministic stand-in so the LLM path is fully testable without network/tokens.

    Either returns a fixed ``canned`` string, or calls a ``handler(prompt, system)`` you provide.
    """

    provider = "mock"

    def __init__(self, canned: str = "{}", handler: Optional[Callable[[str, Optional[str]], str]] = None,
                 model: str = "mock") -> None:
        super().__init__(model, temperature=0.0)
        self.canned = canned
        self.handler = handler
        self.calls: list[dict] = []

    def complete(self, prompt, *, system=None, max_tokens=1024, json_mode=True) -> LLMResponse:
        self.calls.append({"prompt": prompt, "system": system, "max_tokens": max_tokens})
        text = self.handler(prompt, system) if self.handler else self.canned
        return LLMResponse(text, self.model, self.provider, len(prompt) // 4, len(text) // 4)


__all__ = [
    "LLMClient", "LLMResponse", "make_client", "MockClient",
    "OpenAIClient", "AnthropicClient", "GeminiClient", "OllamaClient",
]
