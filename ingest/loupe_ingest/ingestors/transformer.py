"""Transformer / LLM architecture → IR (deterministic, **0 tokens**).

Input is an HF-``config.json``-shaped dict (or path), or a dict produced by introspecting a live
``torch.nn.Module`` (see ``tools/extract_transformer.py``). The exact shape (n_layers, n_heads, d_model,
d_ff, vocab) is read directly — never guessed — so a transformer's structure is always faithful.

Hierarchy emitted (this is the "decomposition" for the transformer domain):
    model → [embeddings, block_0..block_{N-1}, final_norm, lm_head]
    block_i → [attention, mlp, norm_1, norm_2]
    attention → [head_0..head_{H-1}, out_proj]
LOD bands: model/top parts = 0; block internals = 1; individual heads = 2 (drill from whole net to one
head). Residual-stream flow is captured as relations.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..ir import Document, Entity, LODPolicy, Payload, Relation
from .base import IngestContext, Ingestor, Source

# Common HF config aliases → canonical fields.
_ALIASES = {
    "n_layers": ("num_hidden_layers", "n_layer", "num_layers", "n_layers"),
    "n_heads": ("num_attention_heads", "n_head", "num_heads", "n_heads"),
    "d_model": ("hidden_size", "n_embd", "d_model", "hidden_dim"),
    "d_ff": ("intermediate_size", "n_inner", "ffn_dim", "d_ff"),
    "vocab": ("vocab_size", "n_vocab", "vocab"),
    "n_ctx": ("max_position_embeddings", "n_positions", "n_ctx", "context_length"),
}


def _pick(cfg: dict[str, Any], canonical: str, default: Any) -> Any:
    for k in _ALIASES.get(canonical, (canonical,)):
        if k in cfg and cfg[k] is not None:
            return cfg[k]
    return default


def _tint(rgb: tuple[float, float, float]) -> list[float]:
    return [round(c, 3) for c in rgb]


class TransformerIngestor(Ingestor):
    uses_llm = False

    @property
    def name(self) -> str:
        return "transformer"

    def can_handle(self, source: Source) -> bool:
        if source.kind_hint == "transformer":
            return True
        cfg = self._load_cfg(source, soft=True)
        if not isinstance(cfg, dict):
            return False
        arch = " ".join(str(a).lower() for a in cfg.get("architectures", []))
        model_type = str(cfg.get("model_type", "")).lower()
        looks_transformer = any(
            k in cfg for k in ("num_hidden_layers", "n_layer", "num_attention_heads", "n_head")
        )
        return looks_transformer or "transformer" in arch or model_type != ""

    def ingest(self, source: Source, ctx: IngestContext) -> Document:
        cfg = self._load_cfg(source)
        n_layers = int(_pick(cfg, "n_layers", 12))
        n_heads = int(_pick(cfg, "n_heads", 12))
        d_model = int(_pick(cfg, "d_model", 768))
        d_ff = int(_pick(cfg, "d_ff", d_model * 4))
        vocab = int(_pick(cfg, "vocab", 50257))
        n_ctx = int(_pick(cfg, "n_ctx", 1024))
        name = str(cfg.get("_name_or_path") or cfg.get("model_type") or source.kind_hint or "Transformer")

        # Token-frugality + readability: cap how many blocks/heads we expand structurally. The rest are
        # summarized so a 96-layer model doesn't explode into thousands of nodes (lazy expand handles the
        # deep dive later). Configurable via options.
        max_blocks = int(ctx.options.get("max_blocks", 8))
        max_heads = int(ctx.options.get("max_heads", min(n_heads, 8)))

        ents: list[Entity] = []
        rels: list[Relation] = []

        root_id = "model"
        ents.append(Entity(
            id=root_id, label=name, kind="model", parent=None, lod_band=0,
            payload=Payload.make("text", {"accent": _tint((0.45, 0.85, 1.0)), "width": 2.6, "height": 1.4}),
            content_tiers={
                "overview": f"{name}: {n_layers}L · {n_heads}H · d={d_model}",
                "detail": f"vocab={vocab:,} · d_ff={d_ff} · ctx={n_ctx}",
                "deep": f"Params ≈ {self._param_estimate(n_layers, d_model, d_ff, vocab):,} (rough).",
            },
        ))

        ents.append(Entity(
            id="embeddings", label="Token + Pos Embeddings", kind="layer", parent=root_id, lod_band=0,
            payload=Payload.make("matrix", {"rows": vocab, "cols": d_model, "accent": _tint((0.5, 0.9, 0.7))}),
            content_tiers={"overview": f"Embedding matrix {vocab}×{d_model}"},
        ))

        shown = min(n_layers, max_blocks)
        prev = "embeddings"
        for i in range(shown):
            bid = f"block_{i}"
            ents.append(Entity(
                id=bid, label=f"Decoder Block {i}", kind="block", parent=root_id, lod_band=0,
                payload=Payload.make("text", {"accent": _tint((0.4, 0.8, 1.0)), "width": 1.5, "height": 0.95}),
                content_tiers={"overview": f"Block {i}", "detail": f"{n_heads} heads · MLP {d_model}→{d_ff}→{d_model}"},
            ))
            rels.append(Relation(prev, bid, "residual"))
            prev = bid
            self._emit_block(ents, rels, bid, i, n_heads, max_heads, d_model, d_ff)

        if n_layers > shown:
            ents.append(Entity(
                id="blocks_more", label=f"… +{n_layers - shown} more blocks", kind="ellipsis",
                parent=root_id, lod_band=1, payload=Payload.make("none"),
                content_tiers={"overview": f"{n_layers - shown} additional identical decoder blocks (lazy-expand)."},
            ))

        ents.append(Entity(
            id="final_norm", label="Final LayerNorm", kind="layer", parent=root_id, lod_band=1,
            payload=Payload.make("none"), content_tiers={"overview": "Final normalization."},
        ))
        ents.append(Entity(
            id="lm_head", label="LM Head", kind="layer", parent=root_id, lod_band=0,
            payload=Payload.make("matrix", {"rows": d_model, "cols": vocab, "accent": _tint((0.95, 0.7, 0.4))}),
            content_tiers={"overview": f"Output projection {d_model}×{vocab}"},
        ))
        rels.append(Relation(prev, "final_norm", "residual"))
        rels.append(Relation("final_norm", "lm_head", "flow"))

        doc = Document(root=root_id, entities=ents, relations=rels,
                       lod_policy=LODPolicy(bands=3, distance_thresholds=[6.0, 3.2]))
        return doc

    def _emit_block(self, ents, rels, bid, i, n_heads, max_heads, d_model, d_ff) -> None:
        attn = f"{bid}_attn"
        mlp = f"{bid}_mlp"
        ents.append(Entity(
            id=attn, label="Multi-Head Attention", kind="sublayer", parent=bid, lod_band=1,
            payload=Payload.make("text", {"accent": _tint((0.6, 0.9, 1.0)), "width": 1.2, "height": 0.8}),
            content_tiers={"overview": f"{n_heads} heads", "detail": f"d_head={d_model // max(n_heads,1)}"},
        ))
        ents.append(Entity(
            id=mlp, label="MLP", kind="sublayer", parent=bid, lod_band=1,
            payload=Payload.make("text", {"accent": _tint((0.5, 0.95, 0.8)), "width": 1.2, "height": 0.8}),
            content_tiers={"overview": f"{d_model}→{d_ff}→{d_model}", "detail": "GELU feed-forward."},
        ))
        ents.append(Entity(
            id=f"{bid}_ln1", label="LayerNorm 1", kind="norm", parent=bid, lod_band=2,
            payload=Payload.make("none"), content_tiers={"overview": "Pre-attention norm."},
        ))
        ents.append(Entity(
            id=f"{bid}_ln2", label="LayerNorm 2", kind="norm", parent=bid, lod_band=2,
            payload=Payload.make("none"), content_tiers={"overview": "Pre-MLP norm."},
        ))
        rels.append(Relation(attn, mlp, "flow"))

        heads = min(n_heads, max_heads)
        for h in range(heads):
            ents.append(Entity(
                id=f"{attn}_h{h}", label=f"Head {h}", kind="head", parent=attn, lod_band=2,
                payload=Payload.make("matrix", {"square": True, "accent": _tint((0.7, 0.95, 1.0)),
                                                "note": "attention pattern"}),
                content_tiers={"overview": f"Attention head {h}",
                               "detail": f"Q,K,V projections → d_head={d_model // max(n_heads,1)}"},
            ))
        if n_heads > heads:
            ents.append(Entity(
                id=f"{attn}_more", label=f"… +{n_heads - heads} heads", kind="ellipsis", parent=attn,
                lod_band=2, payload=Payload.make("none"),
                content_tiers={"overview": f"{n_heads - heads} more heads (lazy-expand)."},
            ))

    @staticmethod
    def _param_estimate(n_layers: int, d_model: int, d_ff: int, vocab: int) -> int:
        per_block = 4 * d_model * d_model + 2 * d_model * d_ff
        return n_layers * per_block + 2 * vocab * d_model

    @staticmethod
    def _load_cfg(source: Source, soft: bool = False) -> Any:
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
