import json

from loupe_ingest import Cache, ingest
from loupe_ingest.llm import MockClient, make_client
from loupe_ingest.ingestors import Source, TransformerIngestor


def test_llm_frontier_with_mock_zero_network(tmp_path):
    """A bare concept with no structured source → LLM frontier, exercised via MockClient (0 tokens)."""
    decomposition = {
        "root": "engine",
        "entities": [
            {"id": "engine", "label": "Rocket Engine", "kind": "assembly", "parent": None,
             "lod_band": 0, "payload_type": "text", "overview": "A liquid rocket engine."},
            {"id": "nozzle", "label": "Nozzle", "kind": "part", "parent": "engine",
             "lod_band": 0, "payload_type": "text", "overview": "Expands exhaust."},
            {"id": "pump", "label": "Turbopump", "kind": "part", "parent": "engine",
             "lod_band": 0, "payload_type": "text", "overview": "Pressurizes propellant."},
        ],
        "relations": [{"from": "pump", "to": "nozzle", "kind": "feeds"}],
    }
    mock = MockClient(canned=json.dumps(decomposition))
    cache = Cache(directory=tmp_path / "c", enabled=False)
    doc = ingest("a liquid rocket engine", llm=mock, cache=cache, ground=False)
    doc.validate()
    ids = {e.id for e in doc.entities}
    assert ids == {"engine", "nozzle", "pump"}
    # LLM-built entities carry model/prompt provenance for auditability.
    nozzle = next(e for e in doc.entities if e.id == "nozzle")
    assert nozzle.provenance.model == "mock"
    assert nozzle.provenance.prompt_version
    assert len(mock.calls) == 1


def test_llm_response_is_cached_zero_tokens_on_rerun(tmp_path):
    canned = json.dumps({
        "root": "x",
        "entities": [{"id": "x", "label": "X", "parent": None, "payload_type": "text"}],
    })
    mock = MockClient(canned=canned)
    cache = Cache(directory=tmp_path / "c", enabled=True)
    ingest("some concept", llm=mock, cache=cache, ground=False)
    ingest("some concept", llm=mock, cache=cache, ground=False)
    # Second run served from cache → the LLM was only hit once.
    assert len(mock.calls) == 1


def test_llm_strips_markdown_fence(tmp_path):
    fenced = "```json\n" + json.dumps({
        "root": "r", "entities": [{"id": "r", "label": "R", "parent": None, "payload_type": "text"}],
    }) + "\n```"
    mock = MockClient(canned=fenced)
    cache = Cache(directory=tmp_path / "c", enabled=False)
    doc = ingest("thing", llm=mock, cache=cache, ground=False)
    assert doc.root == "r"


def test_make_client_known_providers():
    for prov in ("gpt", "openai", "sonnet", "anthropic", "claude", "gemini", "google", "ollama", "local"):
        c = make_client(prov)
        assert c.model  # a default model is chosen


def test_make_client_unknown_provider_raises():
    import pytest
    with pytest.raises(ValueError):
        make_client("not-a-provider")


def test_deterministic_beats_llm_in_router(tmp_path):
    """A transformer config must route to the deterministic ingestor, never the LLM."""
    cfg = {"model_type": "gpt2", "n_layer": 2, "n_head": 2, "n_embd": 64}
    mock = MockClient(canned="{}")
    cache = Cache(directory=tmp_path / "c", enabled=False)
    doc = ingest(cfg, cache=cache, llm=mock)
    assert doc.provenance.generator.endswith("transformer")
    assert len(mock.calls) == 0  # LLM never touched


def test_transformer_can_handle_detection():
    ing = TransformerIngestor()
    assert ing.can_handle(Source({"num_hidden_layers": 12, "num_attention_heads": 12}))
    assert not ing.can_handle(Source({"parts": [], "root": "x"}))
