"""Router — pick the most specific ingestor for a source (deterministic-first, LP-013).

Order matters: deterministic ingestors (0 tokens) are tried first; the LLM frontier is the last resort.
This is what keeps the common path free.
"""
from __future__ import annotations

from typing import Sequence

from .ingestors import (
    ArxivIngestor,
    BlueprintIngestor,
    GitHubIngestor,
    Ingestor,
    LLMIngestor,
    ModelArchIngestor,
    PDBIngestor,
    Source,
    TransformerIngestor,
)


def default_ingestors() -> list[Ingestor]:
    # Deterministic first (specific → general); LLM frontier last.
    return [
        ModelArchIngestor(),
        TransformerIngestor(),
        BlueprintIngestor(),
        ArxivIngestor(),
        PDBIngestor(),
        GitHubIngestor(),
        LLMIngestor(),
    ]


class Router:
    def __init__(self, ingestors: Sequence[Ingestor] | None = None) -> None:
        self.ingestors = list(ingestors) if ingestors is not None else default_ingestors()

    def route(self, source: Source) -> Ingestor:
        for ing in self.ingestors:
            try:
                if ing.can_handle(source):
                    return ing
            except Exception:  # noqa: BLE001 - a probe must never crash routing
                continue
        # Should be unreachable while LLMIngestor.can_handle is permissive, but be explicit.
        raise LookupError(f"No ingestor could handle source: {source!r}")
