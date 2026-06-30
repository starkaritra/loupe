"""Protein structure (RCSB PDB) → IR (deterministic, **0 tokens**, real web data).

Source forms: ``pdb:1CRN`` / ``pdb:4HHB`` or ``kind_hint='pdb'``. Downloads the real ``.pdb`` file and
builds the actual 3D structure — this is "see the actual parts" for molecular biology:

    structure → chain_A, chain_B, ...        (containment hierarchy)
    each chain carries a `graph` payload: nodes = Cα atoms at their REAL coordinates,
                                           edges = peptide backbone bonds (consecutive residues)

Cα-only (one node per residue) keeps node counts sane while preserving the recognizable fold/backbone
trace. Coordinates are used as-is; the graph lens auto-centers/scales per chain.
"""
from __future__ import annotations

import urllib.request
from typing import Any, Optional

from ..ir import Document, Entity, LODPolicy, Payload, Relation
from .base import IngestContext, Ingestor, Source

_DOWNLOAD = "https://files.rcsb.org/download/{}.pdb"
_META = "https://data.rcsb.org/rest/v1/core/entry/{}"

# A few distinct chain tints so multi-chain structures read clearly.
_CHAIN_TINTS = [
    [0.45, 0.85, 1.0], [1.0, 0.65, 0.45], [0.55, 1.0, 0.7],
    [0.9, 0.6, 1.0], [1.0, 0.9, 0.5], [0.6, 0.95, 0.95],
]


class PDBIngestor(Ingestor):
    uses_llm = False

    @property
    def name(self) -> str:
        return "pdb"

    @staticmethod
    def _extract_id(raw: Any) -> Optional[str]:
        if not isinstance(raw, str):
            return None
        s = raw.strip()
        if s.lower().startswith("pdb:"):
            s = s.split(":", 1)[1]
        s = s.strip().upper()
        return s if len(s) == 4 and s.isalnum() else None

    def can_handle(self, source: Source) -> bool:
        if source.kind_hint == "pdb":
            return self._extract_id(source.raw) is not None
        raw = source.raw
        return isinstance(raw, str) and raw.lower().startswith("pdb:") and self._extract_id(raw) is not None

    def ingest(self, source: Source, ctx: IngestContext) -> Document:
        pdb_id = self._extract_id(source.raw)
        if not pdb_id:
            raise ValueError(f"Could not parse a 4-char PDB id from {source.raw!r}")

        text = ctx.cache.memoize(ctx.cache.key("pdb-file", pdb_id), lambda: self._fetch(pdb_id)) \
            if ctx.cache else self._fetch(pdb_id)
        title = ctx.cache.memoize(ctx.cache.key("pdb-title", pdb_id), lambda: self._fetch_title(pdb_id)) \
            if ctx.cache else self._fetch_title(pdb_id)

        chains = self._parse_ca(text)
        if not chains:
            raise ValueError(f"No Cα atoms parsed from PDB {pdb_id}")

        ents: list[Entity] = []
        rels: list[Relation] = []
        root_id = "structure"
        total_res = sum(len(v) for v in chains.values())
        ents.append(Entity(
            id=root_id, label=title or f"PDB {pdb_id}", kind="structure", parent=None, lod_band=0,
            payload=Payload.make("text", {"accent": _CHAIN_TINTS[0], "width": 2.6, "height": 1.3}),
            content_tiers={
                "overview": title or f"Protein {pdb_id}",
                "detail": f"{len(chains)} chain(s) · {total_res} residues (Cα backbone)",
            },
        ))
        for idx, (chain_id, residues) in enumerate(chains.items()):
            tint = _CHAIN_TINTS[idx % len(_CHAIN_TINTS)]
            nodes = [{"pos": r["pos"]} for r in residues]
            edges = [[i, i + 1] for i in range(len(residues) - 1)]  # backbone bonds
            ents.append(Entity(
                id=f"chain_{chain_id}", label=f"Chain {chain_id}", kind="chain", parent=root_id, lod_band=0,
                payload=Payload.make("graph", {
                    "nodes": nodes, "edges": edges,
                    "node_color": tint, "edge_color": tint + [0.5],
                    "node_radius": 0.06, "glow": 1.4,
                }),
                content_tiers={"overview": f"Chain {chain_id}: {len(residues)} residues",
                               "detail": "Cα backbone trace with peptide bonds."},
            ))
            if idx > 0:
                rels.append(Relation(f"chain_{list(chains)[0]}", f"chain_{chain_id}", "connects"))

        doc = Document(root=root_id, entities=ents, relations=rels,
                       lod_policy=LODPolicy(bands=3, distance_thresholds=[6.0, 3.2]))
        doc.provenance = None
        return doc

    @staticmethod
    def _parse_ca(text: str) -> dict[str, list[dict]]:
        """Parse ATOM records, keeping Cα atoms per chain (PDB column-fixed format)."""
        chains: dict[str, list[dict]] = {}
        for line in text.splitlines():
            if not line.startswith("ATOM"):
                continue
            atom_name = line[12:16].strip()
            if atom_name != "CA":
                continue
            chain_id = line[21:22].strip() or "A"
            try:
                x = float(line[30:38]); y = float(line[38:46]); z = float(line[46:54])
            except ValueError:
                continue
            chains.setdefault(chain_id, []).append({"pos": [x, y, z]})
        return chains

    @staticmethod
    def _fetch(pdb_id: str) -> str:
        req = urllib.request.Request(_DOWNLOAD.format(pdb_id), headers={"User-Agent": "loupe-ingest/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            return r.read().decode("utf-8", "ignore")

    @staticmethod
    def _fetch_title(pdb_id: str) -> str:
        import json
        try:
            req = urllib.request.Request(_META.format(pdb_id), headers={"User-Agent": "loupe-ingest/0.1"})
            with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
                data = json.loads(r.read().decode("utf-8"))
            return (data.get("struct", {}) or {}).get("title", "") or f"PDB {pdb_id}"
        except Exception:  # noqa: BLE001 - title is cosmetic
            return f"PDB {pdb_id}"
