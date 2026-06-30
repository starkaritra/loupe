"""loupe-ingest — the universal function that compiles ANYTHING into loupe-ir/v1.

Standalone and independent: depends on neither Copilot nor the Godot engine. Deterministic-first and
token-frugal; the LLM (GPT/Sonnet/Gemini/Ollama) is optional and only used at the frontier.

    from loupe_ingest import ingest
    doc = ingest("model_config.json")          # deterministic, 0 tokens
    doc = ingest("a rocket engine", llm=make_client("ollama"))  # grounded LLM frontier
    open("out.ir.json", "w").write(doc.to_json())
"""
from __future__ import annotations

from .cache import Cache
from .ingestors import Source
from .ir import Document, Entity, IRError, Payload, Provenance, Relation
from .llm import make_client
from .pipeline import ingest
from .router import Router, default_ingestors

__version__ = "0.1.0"

__all__ = [
    "ingest", "Document", "Entity", "Payload", "Relation", "Provenance", "IRError",
    "Source", "Router", "default_ingestors", "Cache", "make_client", "__version__",
]
