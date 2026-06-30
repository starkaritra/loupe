# Loupe — Model Architecture arm (divide & conquer, arm #1)

Polish ONE arm to high quality, then move on. Current arm: **Model Architecture** (replaces the old
"transformer" config-decomposer). North star: it should feel REAL — see self-attention computing, LSTM
gates flowing, ResNet layers/params — held in your hands.

## Locked decisions (this arm)
- Web-first adapter, **LLM minimized**: deterministic family templates + real dims; LLM only fills gaps.
- **One universal adapter per arm**: `model_architecture` ingestor handles ALL model families. Each
  future arm gets its own single adapter.
- Dedicated dataflow/diagram + mechanism lenses (not just graph boxes). Adherence-to-reality + tactile.
- First exemplar to nail: **Transformer self-attention** (mechanism visibly working, drill-in, real params).

## Build order
1. [exemplar] `attention` lens — Q/K/V → QKᵀ → softmax → ·V visibly animating, real d_model/heads. ← NOW
2. dataflow lens — model-level boxes + arrows + lanes (stages), LOD = abstraction level.
3. model_architecture adapter (universal): name → family template + dims (web/HF, min LLM) → IR.
4. expand families: ViT, ResNet/CNN/AlexNet, GRU/LSTM, Stable Diffusion. Each = a template, no engine change.

## Verify
Godot 4.7 headless: --import then --script res://tools/verify.gd  → RESULT PASS. + pytest in ingest/.
