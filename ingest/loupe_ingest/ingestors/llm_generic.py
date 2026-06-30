"""LLM frontier ingestor — the UNIVERSAL fallback (LP-013).

Used only when no deterministic ingestor can handle a source (an unstructured doc, scraped prose, or a
bare concept like "a rocket engine"). The LLM reads the (optionally web-acquired, grounded) material and
emits a loupe-ir/v1 skeleton: entities + hierarchy + relations + content tiers + payload types.

Token-frugality: compact system prompt, JSON-constrained output, bounded ``max_tokens``, and the whole
call is cached by input-hash upstream (pipeline) so re-runs cost 0 tokens. Every entity is stamped with
model/temperature/prompt-version provenance and (when grounded) a source citation, so output is auditable
rather than blindly trusted.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from ..ir import Document, Entity, LODPolicy, Payload, Provenance, Relation
from .base import IngestContext, Ingestor, Source

PROMPT_VERSION = "decompose/v1"

# The UNIVERSAL decomposition rubric — domain-agnostic. Optional per-domain hints are appended by the
# router/pipeline as data, never code.
_SYSTEM = (
    "You decompose ANY system into a nested, explodable structure for a 3D exploded-view explorer. "
    "Output ONE JSON object: {\"root\": id, \"entities\": [...], \"relations\": [...]}. "
    "Each entity: {id, label, kind, parent (null for root), lod_band (0 top .. deeper=larger), "
    "payload_type (one of: none,text,mesh,signal,image,equation,table,point_cloud,graph,matrix), "
    "overview, detail}. Rules: build a real containment hierarchy (whole -> parts -> sub-parts); "
    "assign lod_band so coarse parts are 0 and fine detail is deeper; keep ids short and unique; "
    "ground every fact ONLY in the provided context; do NOT invent specifics you cannot support. "
    "Be concise. No prose outside the JSON."
)


class LLMIngestor(Ingestor):
    uses_llm = True

    @property
    def name(self) -> str:
        return "llm"

    def can_handle(self, source: Source) -> bool:
        # Frontier fallback: handles anything textual/queryable, but the router only reaches it last.
        return isinstance(source.raw, (str, dict))

    def build_prompt(self, source: Source, context: str, hint: str) -> str:
        target = source.raw if isinstance(source.raw, str) else json.dumps(source.raw)[:2000]
        parts = [f"TARGET TO VISUALIZE: {target}"]
        if hint:
            parts.append(f"DOMAIN HINT: {hint}")
        if context:
            parts.append(f"GROUNDING CONTEXT (use only these facts):\n{context[:6000]}")
        parts.append("Produce the JSON decomposition now.")
        return "\n\n".join(parts)

    def ingest(self, source: Source, ctx: IngestContext) -> Document:
        if ctx.llm is None:
            raise RuntimeError(
                "No deterministic ingestor matched and no LLM client is configured. "
                "Pass --provider (gpt|sonnet|gemini|ollama) or provide a structured source."
            )
        context = str(ctx.options.get("grounding", ""))
        hint = str(ctx.options.get("domain_hint", source.kind_hint))
        prompt = self.build_prompt(source, context, hint)
        max_tokens = int(ctx.options.get("max_tokens", 2048))

        def _call() -> str:
            return ctx.llm.complete(prompt, system=_SYSTEM, max_tokens=max_tokens, json_mode=True).text

        # Cache by (system, prompt, model) → re-runs cost 0 tokens and are reproducible.
        if ctx.cache is not None:
            key = ctx.cache.key("llm-ingest", PROMPT_VERSION, _SYSTEM, prompt, ctx.llm.model)
            raw = ctx.cache.memoize(key, _call)
        else:
            raw = _call()

        spec = self._parse(raw)
        return self._to_document(spec, source, ctx)

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw[raw.find("{"):]
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"LLM did not return JSON: {raw[:200]!r}")
        return json.loads(raw[start:end + 1])

    def _to_document(self, spec: dict[str, Any], source: Source, ctx: IngestContext) -> Document:
        model = getattr(ctx.llm, "model", "")
        temp = getattr(ctx.llm, "temperature", None)
        prov = Provenance(source=source.origin or "llm", generator="LLMIngestor",
                          model=model, temperature=temp, prompt_version=PROMPT_VERSION)
        ents: list[Entity] = []
        for e in spec.get("entities", []):
            if not isinstance(e, dict) or not e.get("id"):
                continue
            ptype = str(e.get("payload_type", "text"))
            tiers = {}
            if e.get("overview"):
                tiers["overview"] = str(e["overview"])
            if e.get("detail"):
                tiers["detail"] = str(e["detail"])
            ents.append(Entity(
                id=str(e["id"]),
                label=str(e.get("label", e["id"])),
                kind=str(e.get("kind", "")),
                parent=e.get("parent"),
                lod_band=int(e.get("lod_band", 0) or 0),
                payload=Payload.make(ptype if ptype != "mesh" else "text"),  # LLM can't author geometry
                content_tiers=tiers,
                provenance=prov,
            ))
        rels = [Relation(str(r["from"]), str(r["to"]), str(r.get("kind", "relates_to")))
                for r in spec.get("relations", []) if isinstance(r, dict) and r.get("from") and r.get("to")]
        root = str(spec.get("root") or (ents[0].id if ents else ""))
        return Document(root=root, entities=ents, relations=rels,
                        lod_policy=LODPolicy(bands=3, distance_thresholds=[5.5, 3.0]))
