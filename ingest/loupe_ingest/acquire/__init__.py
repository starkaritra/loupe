"""Web acquisition (Acquire stage) — optional grounding for the LLM frontier.

Kept dependency-light: tries the Wikipedia REST API (structured, authoritative, no key) first, which is
the cheapest path to grounded facts for a "visualize <concept>" query. Generic scraping can be added
later behind the same function. Returns plain text used as grounding context (and cited in provenance).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class Acquired:
    text: str
    source_url: str


def wikipedia_summary(query: str, timeout: int = 20) -> Optional[Acquired]:
    """Fetch a Wikipedia summary for a concept. Authoritative, structured, no API key, low tokens."""
    title = urllib.parse.quote(query.strip().replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    req = urllib.request.Request(url, headers={"User-Agent": "loupe-ingest/0.1 (grounding)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            data = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - acquisition is best-effort; ground if we can, else proceed
        return None
    extract = data.get("extract") or ""
    if not extract:
        return None
    return Acquired(text=extract, source_url=data.get("content_urls", {}).get("desktop", {}).get("page", url))


def hf_config(model_id: str, timeout: int = 20) -> Optional[dict]:
    """Fetch a model's HuggingFace ``config.json`` (public, no API key) for real architecture dims.

    Web-first + deterministic: the returned dict is the model's own published config (faithful, not
    guessed). Best-effort — returns None on any failure so the caller falls back to family defaults
    (keeps the pipeline fully offline-capable and $0).
    """
    mid = model_id.strip().strip("/")
    url = f"https://huggingface.co/{urllib.parse.quote(mid)}/resolve/main/config.json"
    req = urllib.request.Request(url, headers={"User-Agent": "loupe-ingest/0.1 (config)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            data = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - best-effort; offline/unknown model -> defaults
        return None
    return data if isinstance(data, dict) else None


def acquire(query: str) -> Optional[Acquired]:
    """Best-effort grounding for a free-text target. Extend with more sources as needed."""
    return wikipedia_summary(query)
