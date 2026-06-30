import json

import pytest

from loupe_ingest import ingest, Cache
from loupe_ingest.ir import Document, Entity, IRError, Payload, Relation


@pytest.fixture
def no_cache(tmp_path):
    return Cache(directory=tmp_path / "c", enabled=False)


def test_transformer_from_config_zero_tokens(no_cache):
    cfg = {
        "_name_or_path": "gpt2",
        "model_type": "gpt2",
        "n_layer": 4,
        "n_head": 8,
        "n_embd": 256,
        "n_inner": 1024,
        "vocab_size": 50257,
        "n_positions": 1024,
    }
    doc = ingest(cfg, kind_hint="transformer", cache=no_cache, llm=None)
    doc.validate()
    ids = {e.id for e in doc.entities}
    assert doc.root == "model"
    assert "embeddings" in ids and "lm_head" in ids
    assert "block_0" in ids and "block_3" in ids
    # heads drilled under a block's attention
    assert "block_0_attn_h0" in ids
    # provenance stamped, no LLM model recorded (deterministic path)
    assert doc.provenance.hash
    assert doc.provenance.generator.endswith("transformer")


def test_transformer_caps_blocks_and_heads(no_cache):
    cfg = {"model_type": "llama", "num_hidden_layers": 96, "num_attention_heads": 96,
           "hidden_size": 1024, "intermediate_size": 4096, "vocab_size": 32000}
    doc = ingest(cfg, kind_hint="transformer", cache=no_cache,
                 options={"max_blocks": 3, "max_heads": 2})
    ids = {e.id for e in doc.entities}
    assert "block_2" in ids and "block_3" not in ids
    assert "blocks_more" in ids
    assert "block_0_attn_h1" in ids and "block_0_attn_h2" not in ids
    assert "block_0_attn_more" in ids


def test_blueprint_bell_nozzle_revolve(no_cache, tmp_path):
    bp = {
        "root": "engine",
        "lod_policy": {"bands": 3, "distance_thresholds": [5.0, 3.0]},
        "parts": [
            {"id": "engine", "label": "Engine", "kind": "assembly",
             "geometry": {"type": "none"}},
            {"id": "nozzle", "label": "Nozzle", "parent": "engine",
             "geometry": {"type": "bell_nozzle", "throat_radius": 0.4, "exit_radius": 1.5,
                          "length": 2.0, "bell": 0.6}},
        ],
        "relations": [{"from": "engine", "to": "nozzle", "kind": "contains"}],
    }
    path = tmp_path / "rocket.blueprint.json"
    path.write_text(json.dumps(bp))
    doc = ingest(str(path), cache=no_cache)
    doc.validate()
    nozzle = next(e for e in doc.entities if e.id == "nozzle")
    assert nozzle.payload.type == "mesh"
    data = nozzle.payload.data
    assert data["shape"] == "revolve"
    profile = data["profile"]
    # Bell flares: first radius == throat, last radius == exit, y descends to -length.
    assert profile[0][0] == pytest.approx(0.4, abs=1e-3)
    assert profile[-1][0] == pytest.approx(1.5, abs=1e-3)
    assert profile[-1][1] == pytest.approx(-2.0, abs=1e-3)


def test_round_trips_to_json_and_back(no_cache):
    cfg = {"model_type": "gpt2", "n_layer": 2, "n_head": 4, "n_embd": 128}
    doc = ingest(cfg, kind_hint="transformer", cache=no_cache)
    blob = json.loads(doc.to_json())
    assert blob["version"] == "loupe-ir/v1"
    assert blob["root"] == "model"
    for e in blob["entities"]:
        assert "id" in e and "payload" in e
        assert e["payload"]["type"] in (
            "none", "text", "mesh", "signal", "image", "equation", "table",
            "point_cloud", "graph", "matrix",
        )


def test_validation_catches_bad_parent():
    doc = Document(
        root="a",
        entities=[
            Entity(id="a", label="A"),
            Entity(id="b", label="B", parent="ghost"),
        ],
    )
    with pytest.raises(IRError):
        doc.validate()


def test_validation_catches_duplicate_ids():
    doc = Document(root="a", entities=[Entity(id="a", label="A"), Entity(id="a", label="A2")])
    with pytest.raises(IRError):
        doc.validate()
