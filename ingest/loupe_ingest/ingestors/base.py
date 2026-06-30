"""Ingestor contract — the universal seam (LP-011/LP-012).

An Ingestor maps ONE kind of source into a ``loupe-ir/v1`` Document. Universality is the open set of
ingestors behind this fixed interface, NOT any single mega-parser. Deterministic ingestors
(transformer config, blueprint, code AST) cost 0 tokens; the LLM ingestor is the universal frontier
fallback. The router picks the most specific ingestor that ``can_handle`` a source.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..ir import Document


class Source:
    """A thing to visualize. Either a concrete artifact (path/dict) or a free-text query to acquire."""

    def __init__(self, raw: Any, *, kind_hint: str = "", origin: str = "") -> None:
        self.raw = raw            # path str | dict | parsed object | free-text query
        self.kind_hint = kind_hint  # optional explicit domain hint ("transformer", "blueprint", ...)
        self.origin = origin      # where raw came from (file path, url), for provenance

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Source(kind_hint={self.kind_hint!r}, origin={self.origin!r})"


class Ingestor(ABC):
    """Base class. Subclasses declare a name, whether they can handle a source, and how to ingest it."""

    #: deterministic ingestors set this False (no tokens); the LLM frontier sets it True.
    uses_llm: bool = False

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def can_handle(self, source: Source) -> bool: ...

    @abstractmethod
    def ingest(self, source: Source, ctx: "IngestContext") -> Document: ...


class IngestContext:
    """Shared services handed to every ingestor (cache, optional LLM client, options)."""

    def __init__(self, cache: Any = None, llm: Any = None, options: dict[str, Any] | None = None) -> None:
        self.cache = cache
        self.llm = llm
        self.options = options or {}
