"""Provider-agnostic LLM client (LP-013).

One tiny interface over **OpenAI (gpt), Anthropic (sonnet), Google (gemini), and Ollama (local)**.
Providers are **lazy-imported**, so the package needs ZERO LLM dependencies unless you actually use one.
The LLM is OFF by default — deterministic ingestors are the common, $0 path. Token-frugality is built in:
callers pass tight ``max_tokens`` and prefer JSON-constrained output, and the pipeline caches every call
by input-hash so re-runs cost nothing.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient(ABC):
    """Minimal completion interface. Implementations keep temperature=0 by default for reproducibility."""

    provider: str = ""

    def __init__(self, model: str, temperature: float = 0.0) -> None:
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def complete(self, prompt: str, *, system: Optional[str] = None, max_tokens: int = 1024,
                 json_mode: bool = True) -> LLMResponse: ...


# --------------------------------------------------------------------------- providers

class OpenAIClient(LLMClient):
    provider = "openai"

    def complete(self, prompt, *, system=None, max_tokens=1024, json_mode=True) -> LLMResponse:
        from openai import OpenAI  # lazy
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        kwargs = {"model": self.model, "messages": messages, "temperature": self.temperature,
                  "max_tokens": max_tokens}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        u = resp.usage
        return LLMResponse(resp.choices[0].message.content or "", self.model, self.provider,
                           getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))


class AnthropicClient(LLMClient):
    provider = "anthropic"

    def complete(self, prompt, *, system=None, max_tokens=1024, json_mode=True) -> LLMResponse:
        import anthropic  # lazy
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        if json_mode:
            prompt = prompt + "\n\nRespond with a single valid JSON object only."
        resp = client.messages.create(
            model=self.model, max_tokens=max_tokens, temperature=self.temperature,
            system=system or anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        u = resp.usage
        return LLMResponse(text, self.model, self.provider,
                           getattr(u, "input_tokens", 0), getattr(u, "output_tokens", 0))


class GeminiClient(LLMClient):
    provider = "gemini"

    def complete(self, prompt, *, system=None, max_tokens=1024, json_mode=True) -> LLMResponse:
        import google.generativeai as genai  # lazy
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
        gen_config: dict = {"temperature": self.temperature, "max_output_tokens": max_tokens}
        if json_mode:
            gen_config["response_mime_type"] = "application/json"
        model = genai.GenerativeModel(self.model, system_instruction=system, generation_config=gen_config)
        resp = model.generate_content(prompt)
        return LLMResponse(resp.text, self.model, self.provider)


class OllamaClient(LLMClient):
    """Local model via Ollama's HTTP API. **$0, offline, zero API tokens.** Uses stdlib urllib (no dep)."""

    provider = "ollama"

    def __init__(self, model: str, temperature: float = 0.0, host: Optional[str] = None) -> None:
        super().__init__(model, temperature)
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def complete(self, prompt, *, system=None, max_tokens=1024, json_mode=True) -> LLMResponse:
        import json as _json
        import urllib.request  # lazy/stdlib
        body = {
            "model": self.model, "prompt": prompt, "system": system or "", "stream": False,
            "options": {"temperature": self.temperature, "num_predict": max_tokens},
        }
        if json_mode:
            body["format"] = "json"
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=_json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (local trusted host)
            data = _json.loads(r.read().decode("utf-8"))
        return LLMResponse(data.get("response", ""), self.model, self.provider,
                           data.get("prompt_eval_count", 0), data.get("eval_count", 0))


_PROVIDERS: dict[str, type[LLMClient]] = {
    "openai": OpenAIClient, "gpt": OpenAIClient,
    "anthropic": AnthropicClient, "sonnet": AnthropicClient, "claude": AnthropicClient,
    "gemini": GeminiClient, "google": GeminiClient,
    "ollama": OllamaClient, "local": OllamaClient,
}

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini", "anthropic": "claude-3-5-sonnet-latest",
    "gemini": "gemini-1.5-flash", "ollama": "llama3.1",
}


def make_client(provider: str, model: Optional[str] = None, temperature: float = 0.0,
                **kwargs) -> LLMClient:
    """Factory: ``make_client('sonnet')`` / ``('gpt','gpt-4o')`` / ``('ollama','llama3.1')``.

    Raises ValueError for unknown providers. Does NOT import the SDK until ``complete`` is called.
    """
    key = provider.lower()
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown LLM provider {provider!r}. Known: {sorted(set(_PROVIDERS))}")
    canonical = cls.provider
    chosen = model or _DEFAULT_MODELS.get(canonical, "")
    return cls(chosen, temperature=temperature, **kwargs)
