"""Typed ``loupe-ir/v1`` representation + validation + JSON emission.

This mirrors the engine's schema (``ir/loupe-ir.schema.json``) exactly: the Python package and the Godot
engine are independent and meet ONLY at this contract. Keep the two in lock-step when either changes.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

IR_VERSION = "loupe-ir/v1"

PAYLOAD_TYPES = (
    "none", "mesh", "text", "signal", "image", "equation", "table", "point_cloud", "graph", "matrix",
    "volume", "attention", "conv",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Provenance:
    """How an artifact was produced — the reproducibility/auditability stamp.

    For LLM-derived entities, ``model``/``temperature``/``prompt_version`` make the result reproducible;
    ``source`` cites where the facts came from (resists "is this hallucinated?").
    """

    source: str = ""
    hash: str = ""
    generated_at: str = ""
    generator: str = ""
    model: str = ""
    temperature: Optional[float] = None
    prompt_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k in ("source", "hash", "generated_at", "generator", "model", "prompt_version"):
            v = getattr(self, k)
            if v:
                d[k] = v
        if self.temperature is not None:
            d["temperature"] = self.temperature
        return d


@dataclass
class Payload:
    type: str = "none"
    data: Any = None
    ref: str = ""
    _has_data: bool = field(default=False, repr=False)

    @staticmethod
    def make(type: str, data: Any = None, ref: str = "") -> "Payload":
        p = Payload(type=type, ref=ref)
        if data is not None:
            p.data = data
            p._has_data = True
        return p

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type}
        if self._has_data:
            d["data"] = self.data
        if self.ref:
            d["ref"] = self.ref
        return d


@dataclass
class Placement:
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rot: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {"pos": list(self.pos), "rot": list(self.rot), "scale": list(self.scale)}


@dataclass
class Entity:
    id: str
    label: str
    kind: str = ""
    parent: Optional[str] = None
    placement: Optional[Placement] = None
    lod_band: int = 0
    payload: Payload = field(default_factory=Payload)
    content_tiers: dict[str, str] = field(default_factory=dict)
    provenance: Optional[Provenance] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "label": self.label}
        if self.kind:
            d["kind"] = self.kind
        d["parent"] = self.parent
        if self.placement is not None:
            d["placement"] = self.placement.to_dict()
        d["lod_band"] = self.lod_band
        d["payload"] = self.payload.to_dict()
        if self.content_tiers:
            d["content_tiers"] = self.content_tiers
        if self.provenance is not None:
            d["provenance"] = self.provenance.to_dict()
        return d


@dataclass
class Relation:
    from_id: str
    to_id: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return {"from": self.from_id, "to": self.to_id, "kind": self.kind}


@dataclass
class LODPolicy:
    bands: int = 3
    distance_thresholds: list[float] = field(default_factory=lambda: [5.5, 3.0])

    def to_dict(self) -> dict[str, Any]:
        return {"bands": self.bands, "distance_thresholds": list(self.distance_thresholds)}


class IRError(ValueError):
    """Raised when a document violates the loupe-ir/v1 contract."""


@dataclass
class Document:
    root: str
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    lod_policy: LODPolicy = field(default_factory=LODPolicy)
    provenance: Optional[Provenance] = None
    version: str = IR_VERSION

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "version": self.version,
            "root": self.root,
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "lod_policy": self.lod_policy.to_dict(),
        }
        if self.provenance is not None:
            d["provenance"] = self.provenance.to_dict()
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def validate(self) -> "Document":
        """Schema-shape + referential-integrity checks (mirrors the engine's IRLoader)."""
        if self.version != IR_VERSION:
            raise IRError(f"Unsupported IR version: {self.version!r}")
        if not self.entities:
            raise IRError("Document has no entities")
        ids: set[str] = set()
        for e in self.entities:
            if not e.id:
                raise IRError("Entity with empty id")
            if e.id in ids:
                raise IRError(f"Duplicate entity id: {e.id!r}")
            ids.add(e.id)
            if e.payload.type not in PAYLOAD_TYPES:
                raise IRError(f"Entity {e.id!r}: unknown payload type {e.payload.type!r}")
        if self.root not in ids:
            raise IRError(f"Root entity {self.root!r} not in entities")
        for e in self.entities:
            if e.parent and e.parent not in ids:
                raise IRError(f"Entity {e.id!r} references missing parent {e.parent!r}")
        for r in self.relations:
            if r.from_id not in ids or r.to_id not in ids:
                raise IRError(f"Relation references missing endpoint: {r.from_id} -> {r.to_id}")
        return self

    def stamp(self, source: str = "", generator: str = "loupe-ingest") -> "Document":
        """Ensure a document-level provenance with a content hash for reproducibility."""
        if self.provenance is None:
            self.provenance = Provenance()
        p = self.provenance
        p.source = p.source or source
        p.generator = p.generator or generator
        p.generated_at = p.generated_at or utc_now()
        if not p.hash:
            # Hash the structural content (entities/relations), independent of provenance fields.
            body = json.dumps(
                {"root": self.root,
                 "entities": [e.to_dict() for e in self.entities],
                 "relations": [r.to_dict() for r in self.relations]},
                sort_keys=True,
            )
            p.hash = sha256_text(body)
        return self
