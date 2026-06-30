"""Tests for the universal model-architecture adapter (LP-022)."""
from __future__ import annotations

import pytest

from loupe_ingest.ingestors.base import IngestContext, Source
from loupe_ingest.ingestors.model_arch import TEMPLATES, ModelArchIngestor, build


def _ctx() -> IngestContext:
    return IngestContext(options={"offline": True})


@pytest.mark.parametrize("name", ["gpt2", "alexnet", "lstm", "stable_diffusion", "mamba", "resnet",
                                  "vit", "bert", "gru", "vae", "gan", "moe", "unet", "seq2seq"])
def test_template_emits_valid_ir(name: str) -> None:
    doc = ModelArchIngestor().ingest(Source(f"modelarch:{name}"), _ctx()).stamp(source=name)
    doc.validate()                                  # schema-shape + referential integrity
    assert doc.root == "model"
    assert any(e.id == "model" for e in doc.entities)
    # every relation endpoint exists; flow wires the stages in order
    ids = {e.id for e in doc.entities}
    for r in doc.relations:
        assert r.from_id in ids and r.to_id in ids


def test_can_handle_only_modelarch() -> None:
    ing = ModelArchIngestor()
    assert ing.can_handle(Source("modelarch:gpt2"))
    assert ing.can_handle(Source("anything", kind_hint="model_architecture"))
    assert not ing.can_handle(Source("pdb:4HHB"))
    assert not ing.can_handle(Source({"num_hidden_layers": 12}))


def test_fuzzy_match_to_family() -> None:
    # "gpt2-medium" should still route to the gpt2 template (substring fallback)
    doc = ModelArchIngestor().ingest(Source("modelarch:gpt2-medium"), _ctx())
    assert any(e.label.startswith("Transformer") or "GPT" in e.label for e in doc.entities)


def test_web_first_dims_from_config() -> None:
    ctx = IngestContext(options={"config": {"num_hidden_layers": 24, "num_attention_heads": 16,
                                            "hidden_size": 1024, "vocab_size": 50257,
                                            "_name_or_path": "gpt2-medium"}})
    doc = ModelArchIngestor().ingest(Source("modelarch:gpt2"), ctx)
    model = next(e for e in doc.entities if e.id == "model")
    assert "24 layers" in model.content_tiers.get("detail", "")
    assert "16 heads" in model.content_tiers.get("detail", "")


def test_internals_become_lod2_children() -> None:
    doc = ModelArchIngestor().ingest(Source("modelarch:lstm"), _ctx())
    gates = [e for e in doc.entities if e.parent == "cell"]
    assert len(gates) == 3
    assert all(e.lod_band == 2 for e in gates)


def test_all_payload_types_are_known() -> None:
    from loupe_ingest.ir import PAYLOAD_TYPES
    for name in TEMPLATES:
        doc = ModelArchIngestor().ingest(Source(f"modelarch:{name}"), _ctx())
        for e in doc.entities:
            assert e.payload.type in PAYLOAD_TYPES


def test_build_is_pure() -> None:
    from loupe_ingest.ingestors.model_arch import _gpt2, _dims_from_name
    spec = _gpt2(_dims_from_name("gpt2", _ctx()))
    d1 = build(spec).to_dict()
    d2 = build(spec).to_dict()
    assert d1 == d2                                 # deterministic, reproducible
