# loupe-ingest

The **universal function** for [Loupe](../architecture.md): `visualize(something) → loupe-ir/v1`.

Point it at *anything* with nested structure — a transformer config, an engineering blueprint, a code
repo, or a bare concept — and it compiles a validated, provenance-stamped IR document the Loupe engine
can render. **Standalone**: depends on neither Copilot nor the Godot engine; they meet only at the IR.

## Design (LP-012 / LP-013)
- **Deterministic-first, token-frugal.** Structured sources (transformer `config.json`, blueprint,
  glTF/code) compile with **0 tokens**. The LLM is a *frontier fallback*, off by default.
- **Provider-agnostic LLM.** One interface over **GPT (OpenAI), Sonnet (Anthropic), Gemini (Google),
  Ollama (local)** — lazy-imported, so the package needs no LLM deps unless you use one.
- **Reproducible.** Cache-by-input-hash → re-runs cost 0 tokens and are identical; every entity carries
  provenance (source, hash, model, temperature, prompt version).

## Pipeline
```
ingest(something)
  Acquire (optional web grounding)
    → Route   (deterministic-first; LLM last)
    → Structure (chosen ingestor → IR)
    → Validate (schema + referential integrity)
    → Stamp provenance
  → loupe-ir/v1 JSON
```

## Use
```bash
pip install -e .                       # core, zero deps
pip install -e ".[all,test]"           # + API LLM providers + pytest

# Deterministic, 0 tokens:
loupe-ingest model_config.json -o model.ir.json
loupe-ingest rocket.blueprint.json -o rocket.ir.json

# Live web-API ingestors (deterministic, 0 tokens, real data):
loupe-ingest "arxiv:1706.03762"      -o paper.ir.json     # arXiv paper → sections
loupe-ingest "pdb:1CRN"              -o protein.ir.json   # RCSB protein → Cα backbone (graph)
loupe-ingest "github:pallets/flask"  -o repo.ir.json      # repo → file tree

# LLM frontier (only when no structured source exists):
loupe-ingest "a liquid rocket engine" --provider ollama -o engine.ir.json
loupe-ingest "transformer architecture" --provider sonnet --model claude-3-5-sonnet-latest
```
```python
from loupe_ingest import ingest, make_client
doc = ingest("model_config.json")                          # deterministic
doc = ingest("a brain connectome", llm=make_client("gpt")) # grounded LLM frontier
open("out.ir.json", "w").write(doc.to_json())
```

## Ingestors (current)
| Source form | Ingestor | Output | Tokens |
|---|---|---|---|
| HF `config.json` / dict | `transformer` | model→blocks→attention→heads | 0 |
| `*.blueprint.json` | `blueprint` | mechanical parts (computes bell-nozzle/chamber geometry) | 0 |
| `arxiv:<id>` / arxiv URL | `arxiv` | paper → sections + abstract | 0 |
| `pdb:<4-char id>` | `pdb` | structure → chains (real Cα backbone `graph`) | 0 |
| `github:owner/repo` / URL | `github` | repo → dir/file tree | 0 |
| free-text concept | `llm` | grounded decomposition | frontier only |

## Adding a domain
Write an `Ingestor` (`can_handle` + `ingest`) in `loupe_ingest/ingestors/` and add it to
`router.default_ingestors()`. The engine is untouched — universality is the open set of ingestors behind
one fixed IR contract. See `../docs/data-contract.md` for the domain → data → format → payload map.

## Test
```bash
pytest          # fully offline, 0 tokens (LLM path uses a MockClient)
```
