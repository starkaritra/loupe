"""The universal function: ``ingest(something) -> loupe-ir/v1`` (LP-012/LP-013).

Stages: Acquire (optional web grounding) → Route (deterministic-first) → Structure (the chosen ingestor)
→ Validate → Stamp provenance. Deterministic ingestors need no LLM and cost 0 tokens; the LLM frontier is
reached only when nothing structured matches, and even then is grounded + cached.

This module has NO dependency on Copilot or the Godot engine — it only produces an IR document. The
engine (or anything else) consumes the emitted JSON.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .acquire import acquire as web_acquire
from .cache import Cache
from .ingestors import IngestContext, LLMIngestor, Source
from .ir import Document
from .router import Router


def _looks_like_concept_query(raw: Any, origin: str) -> bool:
    """A bare free-text target (not an existing file/dict) → we may web-ground it."""
    if isinstance(raw, dict):
        return False
    if isinstance(raw, (str, Path)):
        p = Path(str(raw))
        return not p.exists()
    return False


def ingest(
    source: Any,
    *,
    kind_hint: str = "",
    origin: str = "",
    llm: Any = None,
    cache: Optional[Cache] = None,
    ground: bool = True,
    domain_hint: str = "",
    options: Optional[dict[str, Any]] = None,
    ingestors: Optional[list] = None,
) -> Document:
    """Compile ``source`` into a validated, provenance-stamped IR Document.

    ``source`` may be a path to a structured file (config.json, blueprint.json), a dict, or a free-text
    target ("a rocket engine"). ``llm`` (a ``loupe_ingest.llm`` client) is only consulted if no
    deterministic ingestor matches. ``cache`` makes LLM/web steps reproducible and token-free on re-run.
    """
    if cache is None:
        cache = Cache()
    if isinstance(source, Source):
        src = source
    else:
        if not origin and isinstance(source, (str, Path)) and Path(str(source)).exists():
            origin = str(source)
        src = Source(source, kind_hint=kind_hint, origin=origin)

    opts: dict[str, Any] = dict(options or {})
    if domain_hint:
        opts["domain_hint"] = domain_hint

    router = Router(ingestors)
    chosen = router.route(src)

    # Ground only when we're about to hand a bare concept to the LLM frontier (keeps tokens minimal).
    if isinstance(chosen, LLMIngestor) and ground and "grounding" not in opts \
            and _looks_like_concept_query(src.raw, src.origin) and isinstance(src.raw, str):
        acq = cache.memoize(
            cache.key("acquire", src.raw),
            lambda: (lambda a: {"text": a.text, "url": a.source_url} if a else {})(web_acquire(src.raw)),
        )
        if acq:
            opts["grounding"] = acq.get("text", "")
            if not src.origin:
                src.origin = acq.get("url", "")

    ctx = IngestContext(cache=cache, llm=llm, options=opts)
    doc = chosen.ingest(src, ctx)
    doc.validate()
    doc.stamp(source=src.origin, generator=f"loupe-ingest/{chosen.name}")
    return doc
