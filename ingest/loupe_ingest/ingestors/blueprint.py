"""Engineering blueprint → IR (deterministic, **0 tokens**).

A blueprint is a compact, engineering-friendly spec (a rocket engine, a pump, any mechanical assembly).
This ingestor carries the DOMAIN MATH that a 1:1 renamer wouldn't: a ``bell_nozzle`` part is described by
throat/exit radius + length and the ingestor COMPUTES the revolved bell profile; a ``chamber`` becomes a
cylinder + dome. Each part becomes its own IR entity (full explode). The engine's ``proc_mesh.gd``
renders the emitted ``revolve``/``tube`` profiles — Python decides "what is it", Godot draws it.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from ..ir import Document, Entity, LODPolicy, Payload, Placement, Relation
from .base import IngestContext, Ingestor, Source

_DEFAULT_TINT = [0.30, 0.72, 1.0]


class BlueprintIngestor(Ingestor):
    uses_llm = False

    @property
    def name(self) -> str:
        return "blueprint"

    def can_handle(self, source: Source) -> bool:
        if source.kind_hint == "blueprint":
            return True
        bp = self._load(source, soft=True)
        return isinstance(bp, dict) and isinstance(bp.get("parts"), list) and "root" in bp

    def ingest(self, source: Source, ctx: IngestContext) -> Document:
        bp = self._load(source)
        ents: list[Entity] = []
        for part in bp.get("parts", []):
            if isinstance(part, dict):
                ents.append(self._part_to_entity(part))
        rels = [Relation(r["from"], r["to"], r.get("kind", "flow"))
                for r in bp.get("relations", []) if isinstance(r, dict)]
        lod = bp.get("lod_policy", {})
        doc = Document(
            root=str(bp.get("root", "")),
            entities=ents,
            relations=rels,
            lod_policy=LODPolicy(
                bands=int(lod.get("bands", 3)),
                distance_thresholds=list(lod.get("distance_thresholds", [5.5, 3.0])),
            ),
        )
        return doc

    def _part_to_entity(self, part: dict[str, Any]) -> Entity:
        geom = part.get("geometry", {}) if isinstance(part.get("geometry"), dict) else {}
        tint = part.get("tint", _DEFAULT_TINT)
        glow = float(part.get("glow", 1.4))
        placement = None
        if isinstance(part.get("placement"), dict):
            pl = part["placement"]
            placement = Placement(
                pos=tuple(pl.get("pos", [0, 0, 0])),
                rot=tuple(pl.get("rot", [0, 0, 0])),
                scale=tuple(pl.get("scale", [1, 1, 1])),
            )
        return Entity(
            id=str(part.get("id", "")),
            label=str(part.get("label", part.get("id", ""))),
            kind=str(part.get("kind", "part")),
            parent=part.get("parent"),
            placement=placement,
            lod_band=int(part.get("lod_band", 0)),
            payload=self._geometry_to_payload(geom, tint, glow),
            content_tiers=part.get("content_tiers", {}),
        )

    def _geometry_to_payload(self, geom: dict[str, Any], tint: list[float], glow: float) -> Payload:
        gtype = str(geom.get("type", "none"))
        if gtype in ("none", "group"):
            return Payload.make("none")
        if gtype == "bell_nozzle":
            profile = self._bell_profile(
                float(geom.get("throat_radius", 0.45)),
                float(geom.get("exit_radius", 1.5)),
                float(geom.get("length", 2.2)),
                float(geom.get("bell", 0.62)),
            )
            return self._revolve(profile, int(geom.get("segments", 56)), tint, glow)
        if gtype == "chamber":
            profile = self._chamber_profile(
                float(geom.get("radius", 0.9)),
                float(geom.get("length", 1.6)),
                bool(geom.get("dome", True)),
                float(geom.get("dome_ratio", 0.85)),
            )
            return self._revolve(profile, int(geom.get("segments", 48)), tint, glow)
        if gtype == "revolve":
            return self._revolve(geom.get("profile", []), int(geom.get("segments", 48)), tint, glow)
        if gtype == "tube":
            return Payload.make("mesh", {
                "shape": "tube", "path": geom.get("path", []),
                "radius": float(geom.get("radius", 0.08)), "sides": int(geom.get("sides", 12)),
                "color": tint, "glow": glow,
            })
        # primitive passthrough
        return Payload.make("mesh", {
            "shape": gtype, "size": geom.get("size", [1, 1, 1]), "color": tint, "glow": glow,
        })

    @staticmethod
    def _revolve(profile: Any, segments: int, tint: list[float], glow: float) -> Payload:
        return Payload.make("mesh", {
            "shape": "revolve", "profile": profile, "segments": segments, "color": tint, "glow": glow,
        })

    @staticmethod
    def _bell_profile(throat: float, exit_r: float, length: float, bell: float, steps: int = 18) -> list[list[float]]:
        """Throat at y=0, flaring to exit at y=-length. ``bell`` < 1 → fast early expansion (the
        characteristic rocket-bell contour). Returns [[radius, y], ...]."""
        out: list[list[float]] = []
        for i in range(steps + 1):
            t = i / steps
            r = throat + (exit_r - throat) * (t ** bell)
            out.append([round(r, 4), round(-length * t, 4)])
        return out

    @staticmethod
    def _chamber_profile(radius: float, length: float, dome: bool, dome_ratio: float, dome_steps: int = 8) -> list[list[float]]:
        out: list[list[float]] = [[radius, 0.0], [radius, length]]
        if dome:
            for k in range(1, dome_steps + 1):
                a = (k / dome_steps) * (math.pi * 0.5)
                out.append([round(radius * math.cos(a), 4), round(length + radius * dome_ratio * math.sin(a), 4)])
        return out

    @staticmethod
    def _load(source: Source, soft: bool = False) -> Any:
        raw = source.raw
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, (str, Path)):
            p = Path(raw)
            if p.exists() and p.suffix == ".json":
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    return None if soft else {}
        return None if soft else {}
