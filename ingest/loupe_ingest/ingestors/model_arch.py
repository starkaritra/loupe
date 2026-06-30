"""Model-architecture adapter — the universal expansion seam for the model arm (LP-022).

Given a model name (``modelarch:gpt2``, ``modelarch:resnet`` ...), emit a ``loupe-ir/v1`` document that
follows the *locked* model-arm UX (LP-020): a left-to-right / depth-stacked flow of named stages, each
with a LaTeX equation below it, that you can DIVE into to reveal its internals (a mechanism or a row of
named sub-parts). The conventions live in ONE compiler (:func:`build`), so adding a model is just data:
describe its stages and (optionally) each stage's internals — the layout, flow wiring, LOD bands,
equation ids and provenance are all filled in automatically.

Design (per project doctrine):
* **Deterministic-first / $0** — templates cost 0 tokens; honest (illustrative dims labelled by the engine).
* **Web-first ready** — :func:`_dims_from_name` hooks real HF-config dimensions when a config is supplied
  via ``ctx.options['config']``; otherwise sensible defaults. The LLM is a *last-resort* gap-filler only.
* **One adapter per arm** — every model family is a template in :data:`TEMPLATES`; the engine is untouched.

Equation ids must exist in ``assets/eqn/index.json`` (rendered by ``tools/render_equations.py``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..ir import Document, Entity, LODPolicy, Payload, Placement, Relation
from .base import IngestContext, Ingestor, Source

# ----------------------------------------------------------------------------- declarative spec


@dataclass
class Part:
    """An internal sub-part revealed when you dive into a stage (a row at L2)."""

    id: str
    label: str
    payload: str = "text"            # text | matrix | attention | conv | graph | none
    data: dict[str, Any] = field(default_factory=dict)
    eqn: str = ""
    kind: str = "head"
    overview: str = ""
    children: list["Part"] = field(default_factory=list)   # deeper level, revealed on a further dive


@dataclass
class Stage:
    """A top-level component in the model's flow (L1), optionally with internals (L2)."""

    id: str
    label: str
    payload: str = "text"
    data: dict[str, Any] = field(default_factory=dict)
    eqn: str = ""
    kind: str = "block"
    overview: str = ""
    detail: str = ""
    internals: list[Part] = field(default_factory=list)


@dataclass
class ModelSpec:
    name: str
    label: str
    overview: str = ""
    detail: str = ""
    deep: str = ""
    stages: list[Stage] = field(default_factory=list)
    layout: str = "row"              # "row" (x axis, default) or "stack" (z axis, like CNN layers)


# ----------------------------------------------------------------------------- the IR compiler


def build(spec: ModelSpec) -> Document:
    """Compile a ModelSpec into a loupe-ir Document following the locked model-arm conventions."""
    ents: list[Entity] = []
    rels: list[Relation] = []

    root_z = 2.0 if spec.layout == "stack" else 0.0
    ents.append(Entity(
        id="model", label=spec.label, kind="model", parent=None, lod_band=0,
        placement=Placement(pos=(0.0, 1.7, root_z)),
        payload=Payload.make("text", {"accent": [0.45, 0.85, 1.0], "width": 2.4, "height": 1.1}),
        content_tiers=_tiers(spec.overview, spec.detail, spec.deep),
    ))

    n = len(spec.stages)
    # Wide animated mechanisms (attention/conv) would overlap neighbours at the overview, so they are
    # shown as a compact CARD at L1 and the real mechanism is nested one level down (revealed on dive).
    MECH = {"attention", "conv"}
    for i, st in enumerate(spec.stages):
        pos = _stage_pos(i, n, spec.layout)
        scale = max(0.7, 1.0 - 0.03 * i)
        payload, data = st.payload, dict(st.data)
        internals = list(st.internals)
        if st.payload in MECH:
            accent = st.data.get("accent", [0.55, 0.95, 1.0])
            # the mechanism owns the stage's sub-parts (e.g. heads) so L2 is JUST the mechanism (clean),
            # and a further dive reveals the sub-parts at L3 — never crammed side-by-side.
            mech = Part(f"{st.id}_mech", st.label, st.payload, dict(st.data), eqn=st.eqn,
                        kind="mechanism", overview=st.overview, children=internals)
            internals = [mech]
            payload, data = "text", {"accent": accent, "width": 1.4, "height": 0.9}
        if st.eqn:
            data.setdefault("eqn", st.eqn)
        ents.append(Entity(
            id=st.id, label=st.label, kind=st.kind, parent="model", lod_band=1,
            placement=Placement(pos=pos, scale=(scale, scale, scale)),
            payload=Payload.make(payload, data if data else None),
            content_tiers=_tiers(st.overview, st.detail),
        ))
        if i > 0:
            rels.append(Relation(spec.stages[i - 1].id, st.id, "flow"))
        _emit_parts(ents, rels, st.id, internals, band=2)

    doc = Document(root="model", entities=ents, relations=rels,
                   lod_policy=LODPolicy(bands=3, distance_thresholds=[7.0, 3.6]))
    return doc


def _emit_parts(ents: list, rels: list, parent_id: str, parts: list, band: int) -> None:
    """Lay a level of internals and recurse into their children (deeper dive = deeper band).

    Parts are placed in a centered row and wired in sequence. A run of many homogeneous "head" parts is
    depth-stacked on the z-axis instead (the MHA look) so it stays legible no matter how many there are.
    """
    m = len(parts)
    if m == 0:
        return
    stack = m > 4 and all(p.kind == "head" for p in parts)   # many parallel heads -> z-stack
    for j, pt in enumerate(parts):
        if stack:
            pos = (0.06 * j, 0.0, (m - 1) / 2.0 * 0.9 - 0.9 * j)
            pscale = 0.5
        else:
            pos = ((j - (m - 1) / 2.0) * 2.2, 0.0, 0.0)
            pscale = 0.85 if pt.kind == "mechanism" else 0.6
        pdata = dict(pt.data)
        if pt.eqn:
            pdata.setdefault("eqn", pt.eqn)
        ents.append(Entity(
            id=pt.id, label=pt.label, kind=pt.kind, parent=parent_id, lod_band=band,
            placement=Placement(pos=pos, scale=(pscale, pscale, pscale)),
            payload=Payload.make(pt.payload, pdata if pdata else None),
            content_tiers=_tiers(pt.overview),
        ))
        if j > 0 and not stack:
            rels.append(Relation(parts[j - 1].id, pt.id, "flow"))
        if pt.children:
            _emit_parts(ents, rels, pt.id, pt.children, band + 1)


def _stage_pos(i: int, n: int, layout: str) -> tuple[float, float, float]:
    if layout == "stack":                       # depth-stacked like CNN layers
        return (0.0, 0.0, 1.2 * (n - 1) / 2.0 - 1.2 * i)
    return ((i - (n - 1) / 2.0) * 3.0, 0.0, 0.0)  # left→right row (wide enough for matrix strips)


def _tiers(overview: str = "", detail: str = "", deep: str = "") -> dict[str, str]:
    d: dict[str, str] = {}
    if overview:
        d["overview"] = overview
    if detail:
        d["detail"] = detail
    if deep:
        d["deep"] = deep
    return d


# ----------------------------------------------------------------------------- helpers for templates


def _causal(seq: int = 8) -> list[list[int]]:
    return [[1 if c <= r else 0 for c in range(seq)] for r in range(seq)]


def mat(rows: int = 0, cols: int = 0, **kw: Any) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if rows:
        d["rows"] = rows
    if cols:
        d["cols"] = cols
    d.update(kw)
    return d


# ----------------------------------------------------------------------------- template library
# Adding a model = add a builder here. Each returns a ModelSpec; the compiler does the rest.

TemplateFn = Callable[[dict[str, Any]], ModelSpec]


def _gpt2(dims: dict[str, Any]) -> ModelSpec:
    nl, nh, dm, vocab = dims["n_layers"], dims["n_heads"], dims["d_model"], dims["vocab"]
    heads = [Part(f"h{i}", "", "matrix", mat(square=True, glow=0.45, values=_causal(),
                  accent=[0.6, 0.9, 1.0]), kind="head", overview=f"head {i}") for i in range(min(nh, 6))]
    return ModelSpec(
        name="gpt2", label=dims.get("title", "Transformer (GPT-2)"),
        overview="Decoder-only LM: text in, next-token out",
        detail=f"{nl} layers; {nh} heads; width {dm}", deep="Embeddings -> blocks -> output head",
        stages=[
            Stage("emb", "Input Embeddings", "matrix", mat(vocab, dm, accent=[0.5, 0.9, 0.7]),
                  eqn="embed", kind="input", overview="token + position to vectors"),
            Stage("attn", "Self-Attention", "attention",
                  {"seq": 8, "d_model": dm, "n_heads": nh, "accent": [0.55, 0.95, 1.0]},
                  eqn="attention", kind="mechanism",
                  overview="tokens mix info from earlier tokens", internals=heads),
            Stage("mlp", "Feed-Forward", "matrix", mat(dm, dm * 4, accent=[0.5, 0.95, 0.8]),
                  eqn="mlp", kind="transform", overview="expand, GELU, project back"),
            Stage("head", "Output Head", "matrix", mat(dm, vocab, accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="scores to vocab; softmax"),
        ])


def _alexnet(_dims: dict[str, Any]) -> ModelSpec:
    conv_internals = [Part("convmech", "convolution", "conv",
                           {"in": 9, "k": 3, "stride": 1, "pad": 1, "accent": [0.6, 0.9, 1.0]},
                           eqn="conv", overview="kernel slides over padded input -> feature map")]
    return ModelSpec(
        name="alexnet", label="AlexNet (CNN)",
        overview="Image classifier: 5 conv + 3 dense", detail="ImageNet 224x224 to 1000 classes",
        deep="conv-pool stack builds features; dense layers classify",
        stages=[
            Stage("in", "Input 224x224x3", "matrix", mat(square=True, accent=[0.6, 0.95, 0.7]),
                  kind="input", overview="RGB image"),
            Stage("c1", "Conv1 + Pool", "matrix", mat(square=True, accent=[0.5, 0.85, 1.0], note="96@11x11"),
                  eqn="conv", kind="conv", overview="96 filters 11x11"),
            Stage("c2", "Conv2 + Pool", "matrix", mat(square=True, accent=[0.5, 0.85, 1.0], note="256@5x5"),
                  eqn="conv", kind="conv", overview="256 filters 5x5"),
            Stage("c3", "Conv3-5", "matrix", mat(square=True, accent=[0.5, 0.85, 1.0], note="384/384/256"),
                  eqn="conv", kind="conv", overview="3 conv 3x3; dive to see convolution",
                  internals=conv_internals),
            Stage("fc6", "FC 4096", "matrix", mat(9216, 4096, accent=[0.5, 0.95, 0.8]),
                  eqn="fc", kind="transform", overview="flatten then dense"),
            Stage("fc8", "Classifier", "matrix", mat(4096, 1000, accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="dense to 1000 classes"),
        ])


def _lstm(_dims: dict[str, Any]) -> ModelSpec:
    return ModelSpec(
        name="lstm", label="LSTM",
        overview="Recurrent net: reads a sequence step by step",
        detail="hidden + cell state carried across time", deep="gates control keep/add/output",
        stages=[
            Stage("emb", "Embeddings", "matrix", mat(30000, 256, accent=[0.5, 0.9, 0.7]),
                  eqn="embed", kind="input", overview="token to vector"),
            Stage("cell", "LSTM Cell", "text", {"accent": [0.5, 0.9, 1.0], "width": 1.3, "height": 0.85},
                  kind="block", overview="dive: highway + 3 gates", internals=[
                      Part("fgate", "forget", "text", {"accent": [1.0, 0.6, 0.6]}, eqn="lstm_f",
                           overview="fraction of memory to keep"),
                      Part("igate", "input + candidate", "text", {"accent": [0.6, 1.0, 0.7]}, eqn="lstm_c",
                           overview="what new info to write"),
                      Part("ogate", "output", "text", {"accent": [0.6, 0.85, 1.0]}, eqn="lstm_o",
                           overview="reveal memory as h(t)"),
                  ]),
            Stage("out", "Output", "matrix", mat(256, 30000, accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="hidden to vocab"),
        ])


def _stable_diffusion(_dims: dict[str, Any]) -> ModelSpec:
    return ModelSpec(
        name="stable_diffusion", label="Stable Diffusion",
        overview="Text-to-image: denoise latent noise into a picture",
        detail="CLIP text + U-Net denoiser + VAE decoder", deep="iteratively predict and subtract noise",
        stages=[
            Stage("clip", "CLIP Text Encoder", "matrix", mat(77, 768, accent=[0.5, 0.9, 0.7]),
                  eqn="clip", kind="input", overview="prompt to conditioning vectors"),
            Stage("unet", "U-Net Denoiser", "text", {"accent": [0.55, 0.95, 1.0], "width": 1.6, "height": 1.0},
                  eqn="unet", kind="mechanism", overview="predicts the noise, x50 steps", internals=[
                      Part("down", "down blocks", "matrix", mat(square=True, glow=0.5, accent=[0.6, 0.9, 1.0],
                           note="encode"), overview="downsample + self-attn"),
                      Part("xattn", "cross-attn", "attention",
                           {"seq": 8, "d_model": 768, "n_heads": 8, "accent": [0.7, 0.95, 1.0]},
                           eqn="diffuse", overview="pixels attend to the prompt"),
                      Part("up", "up blocks", "matrix", mat(square=True, glow=0.5, accent=[0.6, 0.9, 1.0],
                           note="decode"), overview="upsample back, skip links"),
                  ]),
            Stage("vae", "VAE Decoder", "matrix", mat(square=True, accent=[0.95, 0.7, 0.4], note="latent->image"),
                  eqn="vae", kind="output", overview="latent to 512x512 image"),
        ])


def _mamba(_dims: dict[str, Any]) -> ModelSpec:
    return ModelSpec(
        name="mamba", label="Mamba (SSM)",
        overview="Sequence model with linear-time state-space scan (no attention)",
        detail="selective SSM: input-dependent A,B,C", deep="recurrence h = Ah + Bx, y = Ch",
        stages=[
            Stage("emb", "Embeddings", "matrix", mat(50000, 768, accent=[0.5, 0.9, 0.7]),
                  eqn="embed", kind="input", overview="token to vector"),
            Stage("block", "Mamba Block", "text", {"accent": [0.55, 0.95, 1.0], "width": 1.5, "height": 1.0},
                  eqn="mamba_gate", kind="mechanism", overview="linear -> conv1d -> SSM -> gate", internals=[
                      Part("proj", "in-proj + conv", "text", {"accent": [0.7, 0.9, 1.0]}, eqn="fc",
                           overview="expand + depthwise conv1d"),
                      Part("scan", "selective scan", "conv",
                           {"in": 8, "k": 1, "stride": 1, "pad": 0, "accent": [0.6, 0.9, 1.0]},
                           eqn="ssm", overview="state recurrence over time"),
                      Part("gate", "gate", "text", {"accent": [0.95, 0.85, 0.6]}, eqn="mamba_gate",
                           overview="SiLU gate, then project out"),
                  ]),
            Stage("out", "Output Head", "matrix", mat(768, 50000, accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="hidden to vocab"),
        ])


def _resnet(_dims: dict[str, Any]) -> ModelSpec:
    return ModelSpec(
        name="resnet", label="ResNet",
        overview="Deep CNN with residual (skip) connections",
        detail="conv stem -> 4 residual stages -> pool -> FC", deep="skip connections ease deep training",
        stages=[
            Stage("stem", "Conv Stem 7x7", "matrix", mat(square=True, accent=[0.6, 0.95, 0.7]),
                  eqn="conv", kind="input", overview="7x7 conv, stride 2, max-pool"),
            Stage("s1", "Stage 1 (x3)", "matrix", mat(square=True, accent=[0.5, 0.85, 1.0]),
                  eqn="conv", kind="block", overview="residual blocks; dive to see skip", internals=[
                      Part("c1", "conv 3x3", "conv", {"in": 7, "k": 3, "stride": 1, "pad": 1,
                           "accent": [0.6, 0.9, 1.0]}, eqn="conv", overview="first conv"),
                      Part("c2", "conv 3x3", "conv", {"in": 7, "k": 3, "stride": 1, "pad": 1,
                           "accent": [0.6, 0.9, 1.0]}, eqn="conv", overview="second conv"),
                      Part("add", "+ skip", "text", {"accent": [0.6, 1.0, 0.7]},
                           overview="add input back (residual)"),
                  ]),
            Stage("s2", "Stage 2-4", "matrix", mat(square=True, accent=[0.5, 0.85, 1.0]),
                  eqn="conv", kind="block", overview="deeper residual stages"),
            Stage("fc", "Pool + FC", "matrix", mat(2048, 1000, accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="global avg pool to 1000 classes"),
        ])


def _vit(dims: dict[str, Any]) -> ModelSpec:
    heads = [Part(f"h{i}", "", "matrix", mat(square=True, glow=0.45, values=_causal(),
                  accent=[0.6, 0.9, 1.0]), kind="head", overview=f"head {i}") for i in range(6)]
    return ModelSpec(
        name="vit", label="Vision Transformer (ViT)",
        overview="Image as patches -> transformer encoder",
        detail="patchify -> +pos -> encoder -> MLP head", deep="self-attention over image patches",
        stages=[
            Stage("patch", "Patch Embed", "matrix", mat(196, 768, accent=[0.5, 0.9, 0.7]),
                  eqn="embed", kind="input", overview="16x16 patches to tokens + [CLS]"),
            Stage("attn", "Self-Attention", "attention",
                  {"seq": 8, "d_model": 768, "n_heads": 12, "accent": [0.55, 0.95, 1.0]},
                  eqn="attention", kind="mechanism", overview="patches attend to each other",
                  internals=heads),
            Stage("mlp", "MLP", "matrix", mat(768, 3072, accent=[0.5, 0.95, 0.8]),
                  eqn="mlp", kind="transform", overview="feed-forward per token"),
            Stage("head", "MLP Head", "matrix", mat(768, 1000, accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="[CLS] to class scores"),
        ])


def _bert(dims: dict[str, Any]) -> ModelSpec:
    nh, dm, vocab = dims["n_heads"], dims["d_model"], dims["vocab"]
    heads = [Part(f"h{i}", "", "matrix", mat(square=True, glow=0.45, values=_causal(),
                  accent=[0.6, 0.9, 1.0]), kind="head", overview=f"head {i}") for i in range(6)]
    return ModelSpec(
        name="bert", label=dims.get("title", "BERT (encoder)"),
        overview="Bidirectional encoder; masked-language pretraining",
        detail=f"{dims['n_layers']} layers; {nh} heads; width {dm}",
        deep="every token attends to every other (no causal mask)",
        stages=[
            Stage("emb", "Token + Segment + Pos", "matrix", mat(vocab, dm, accent=[0.5, 0.9, 0.7]),
                  eqn="embed", kind="input", overview="word + segment + position embeddings"),
            Stage("attn", "Self-Attention", "attention",
                  {"seq": 8, "d_model": dm, "n_heads": nh, "accent": [0.55, 0.95, 1.0]},
                  eqn="attention", kind="mechanism", overview="bidirectional attention", internals=heads),
            Stage("mlp", "Feed-Forward", "matrix", mat(dm, dm * 4, accent=[0.5, 0.95, 0.8]),
                  eqn="mlp", kind="transform", overview="per-token MLP"),
            Stage("mlm", "MLM Head", "matrix", mat(dm, vocab, accent=[0.95, 0.7, 0.4]),
                  eqn="mlm", kind="output", overview="predict masked tokens"),
        ])


def _gru(_dims: dict[str, Any]) -> ModelSpec:
    return ModelSpec(
        name="gru", label="GRU",
        overview="Gated recurrent unit: simpler than LSTM, no separate cell state",
        detail="reset + update gates", deep="update gate blends old and new hidden state",
        stages=[
            Stage("emb", "Embeddings", "matrix", mat(30000, 256, accent=[0.5, 0.9, 0.7]),
                  eqn="embed", kind="input", overview="token to vector"),
            Stage("cell", "GRU Cell", "text", {"accent": [0.5, 0.9, 1.0], "width": 1.3, "height": 0.85},
                  kind="block", overview="dive: reset + update gates", internals=[
                      Part("rgate", "reset gate", "text", {"accent": [1.0, 0.6, 0.6]}, eqn="lstm_f",
                           overview="how much past to forget"),
                      Part("cand", "candidate", "text", {"accent": [0.6, 1.0, 0.7]}, eqn="lstm_o",
                           overview="proposed new hidden state"),
                      Part("zgate", "update gate", "text", {"accent": [0.6, 0.85, 1.0]}, eqn="lstm_c",
                           overview="blend old and new h"),
                  ]),
            Stage("out", "Output", "matrix", mat(256, 30000, accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="hidden to vocab"),
        ])


def _vae(_dims: dict[str, Any]) -> ModelSpec:
    return ModelSpec(
        name="vae", label="Variational Autoencoder",
        overview="Compress to a probabilistic latent, then reconstruct",
        detail="encoder -> (mu, sigma) -> sample z -> decoder",
        deep="reparameterization makes sampling differentiable",
        stages=[
            Stage("x", "Input", "matrix", mat(square=True, accent=[0.6, 0.95, 0.7]),
                  kind="input", overview="image / data point"),
            Stage("enc", "Encoder", "matrix", mat(square=True, accent=[0.5, 0.85, 1.0]),
                  eqn="vae_enc", kind="block", overview="to mean and variance"),
            Stage("z", "Latent z", "text", {"accent": [0.7, 0.95, 1.0], "width": 1.3, "height": 0.8},
                  eqn="vae_z", kind="mechanism", overview="sample z (reparameterized)", internals=[
                      Part("mu", "mu", "text", {"accent": [0.6, 0.9, 1.0]}, overview="mean of latent"),
                      Part("sig", "sigma", "text", {"accent": [0.6, 1.0, 0.7]}, overview="std of latent"),
                      Part("eps", "z = mu + sigma . eps", "text", {"accent": [0.95, 0.85, 0.6]},
                           eqn="vae_z", overview="reparameterization trick"),
                  ]),
            Stage("dec", "Decoder", "matrix", mat(square=True, accent=[0.95, 0.7, 0.4]),
                  eqn="vae", kind="output", overview="reconstruct the input"),
        ])


def _gan(_dims: dict[str, Any]) -> ModelSpec:
    return ModelSpec(
        name="gan", label="GAN",
        overview="Generator vs Discriminator, trained adversarially",
        detail="G makes fakes from noise; D tells real from fake",
        deep="G improves until D can't distinguish",
        stages=[
            Stage("z", "Noise z", "text", {"accent": [0.6, 0.95, 0.7], "width": 1.1, "height": 0.6},
                  eqn="gan_g", kind="input", overview="random latent vector"),
            Stage("g", "Generator", "matrix", mat(square=True, accent=[0.5, 0.85, 1.0]),
                  eqn="gan_g", kind="mechanism", overview="noise to a fake image", internals=[
                      Part("gu", "upsample blocks", "matrix", mat(square=True, glow=0.5,
                           accent=[0.6, 0.9, 1.0]), overview="transpose-conv upsampling"),
                  ]),
            Stage("d", "Discriminator", "matrix", mat(square=True, accent=[0.95, 0.7, 0.4]),
                  eqn="gan_d", kind="output", overview="real (1) vs fake (0)"),
        ])


def _moe(dims: dict[str, Any]) -> ModelSpec:
    dm, vocab = dims["d_model"], dims["vocab"]
    experts = [Part(f"e{i}", f"expert {i}", "matrix", mat(dm, dm * 4, glow=0.5, accent=[0.6, 0.9, 1.0]),
                    overview="a feed-forward expert") for i in range(4)]
    return ModelSpec(
        name="moe", label="Mixture-of-Experts Transformer",
        overview="Sparse FFN: a router sends each token to a few experts",
        detail=f"{dims['n_layers']} layers; top-k routing", deep="only k experts run per token (sparse)",
        stages=[
            Stage("emb", "Embeddings", "matrix", mat(vocab, dm, accent=[0.5, 0.9, 0.7]),
                  eqn="embed", kind="input", overview="token to vector"),
            Stage("attn", "Self-Attention", "attention",
                  {"seq": 8, "d_model": dm, "n_heads": dims["n_heads"], "accent": [0.55, 0.95, 1.0]},
                  eqn="attention", kind="mechanism", overview="standard attention"),
            Stage("moe", "MoE Feed-Forward", "text", {"accent": [0.55, 0.95, 1.0], "width": 1.5, "height": 1.0},
                  eqn="router", kind="block", overview="router picks top-k experts",
                  internals=[Part("router", "router", "text", {"accent": [0.95, 0.85, 0.6]}, eqn="router",
                                  overview="top-k gating")] + experts),
            Stage("head", "Output Head", "matrix", mat(dm, vocab, accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="scores to vocab"),
        ])


def _unet(_dims: dict[str, Any]) -> ModelSpec:
    return ModelSpec(
        name="unet", label="U-Net",
        overview="Encoder-decoder with skip connections (segmentation/denoising)",
        detail="downsample path -> bottleneck -> upsample path + skips",
        deep="skip links pass fine detail across the U",
        stages=[
            Stage("in", "Input", "matrix", mat(square=True, accent=[0.6, 0.95, 0.7]),
                  kind="input", overview="image"),
            Stage("down", "Down (encoder)", "conv", {"in": 9, "k": 3, "stride": 1, "pad": 1,
                  "accent": [0.5, 0.85, 1.0]}, eqn="conv", kind="block", overview="conv + downsample"),
            Stage("bottle", "Bottleneck", "matrix", mat(square=True, accent=[0.55, 0.95, 1.0]),
                  eqn="conv", kind="mechanism", overview="smallest spatial, richest features"),
            Stage("up", "Up (decoder + skips)", "conv", {"in": 9, "k": 3, "stride": 1, "pad": 1,
                  "accent": [0.5, 0.95, 0.8]}, eqn="conv", kind="block", overview="upsample + concat skip"),
            Stage("out", "Output", "matrix", mat(square=True, accent=[0.95, 0.7, 0.4]),
                  kind="output", overview="per-pixel prediction"),
        ])


def _seq2seq(dims: dict[str, Any]) -> ModelSpec:
    nh, dm = dims["n_heads"], dims["d_model"]
    return ModelSpec(
        name="seq2seq", label="Encoder-Decoder Transformer",
        overview="Seq2seq (translation): encoder reads, decoder writes",
        detail="encoder self-attn + decoder self-attn + cross-attn",
        deep="decoder attends to encoder outputs via cross-attention",
        stages=[
            Stage("enc", "Encoder", "attention",
                  {"seq": 8, "d_model": dm, "n_heads": nh, "accent": [0.5, 0.9, 1.0]},
                  eqn="attention", kind="input", overview="bidirectional self-attention over source"),
            Stage("cross", "Cross-Attention", "attention",
                  {"seq": 8, "d_model": dm, "n_heads": nh, "accent": [0.7, 0.95, 1.0]},
                  eqn="cross_attn", kind="mechanism", overview="target queries attend to source"),
            Stage("dec", "Decoder", "attention",
                  {"seq": 8, "d_model": dm, "n_heads": nh, "accent": [0.55, 0.95, 1.0]},
                  eqn="attention", kind="block", overview="causal self-attention over target"),
            Stage("head", "Output Head", "matrix", mat(dm, dims["vocab"], accent=[0.95, 0.7, 0.4]),
                  eqn="softmax", kind="output", overview="next-token over target vocab"),
        ])


TEMPLATES: dict[str, TemplateFn] = {
    "gpt2": _gpt2, "transformer": _gpt2, "gpt": _gpt2,
    "alexnet": _alexnet, "cnn": _alexnet,
    "lstm": _lstm, "rnn": _lstm,
    "gru": _gru,
    "stable_diffusion": _stable_diffusion, "stablediffusion": _stable_diffusion, "sd": _stable_diffusion,
    "diffusion": _stable_diffusion,
    "mamba": _mamba, "ssm": _mamba,
    "resnet": _resnet,
    "vit": _vit, "visiontransformer": _vit,
    "bert": _bert, "encoder": _bert,
    "vae": _vae, "autoencoder": _vae,
    "gan": _gan,
    "moe": _moe, "mixtureofexperts": _moe,
    "unet": _unet,
    "seq2seq": _seq2seq, "encoderdecoder": _seq2seq, "translation": _seq2seq,
}


# ----------------------------------------------------------------------------- web-first dims (hook)


def _dims_from_name(name: str, ctx: IngestContext) -> dict[str, Any]:
    """Deterministic dims, web-first: explicit config > HF config.json > family defaults (LLM-min).

    Resolution order (each step is faithful, never guessed):
      1. an explicit HF-config dict passed via ``ctx.options['config']`` (caller-supplied);
      2. the model's published ``config.json`` fetched from HuggingFace by id (cached; opt-out with
         ``ctx.options['offline']=True``);
      3. sensible family defaults so the adapter always works offline / for unknown names.
    """
    opts = ctx.options if isinstance(ctx.options, dict) else {}
    cfg = opts.get("config")
    if not isinstance(cfg, dict) and not opts.get("offline"):
        cfg = _fetch_hf_config(name, ctx)
    if isinstance(cfg, dict):
        return {
            "n_layers": int(cfg.get("num_hidden_layers", cfg.get("n_layer", 12))),
            "n_heads": int(cfg.get("num_attention_heads", cfg.get("n_head", 12))),
            "d_model": int(cfg.get("hidden_size", cfg.get("n_embd", 768))),
            "vocab": int(cfg.get("vocab_size", 50257)),
            "title": str(cfg.get("_name_or_path", name)),
        }
    return {"n_layers": 12, "n_heads": 12, "d_model": 768, "vocab": 50257}


def _fetch_hf_config(name: str, ctx: IngestContext) -> Optional[dict[str, Any]]:
    """Fetch + cache a HuggingFace config.json for an architecture name (best-effort, $0)."""
    cache = getattr(ctx, "cache", None)
    key = f"hfcfg:{name.lower()}"
    if cache is not None:
        hit = cache.get(key) if hasattr(cache, "get") else None
        if isinstance(hit, dict):
            return hit
    try:
        from ..acquire import hf_config
    except Exception:  # noqa: BLE001
        return None
    cfg = hf_config(name)
    if isinstance(cfg, dict) and cache is not None and hasattr(cache, "set"):
        try:
            cache.set(key, cfg)
        except Exception:  # noqa: BLE001
            pass
    return cfg


def _normalize(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


class ModelArchIngestor(Ingestor):
    """Universal model-architecture adapter: ``modelarch:<name>`` -> loupe-ir via the template library."""

    uses_llm = False

    @property
    def name(self) -> str:
        return "model_architecture"

    def can_handle(self, source: Source) -> bool:
        if source.kind_hint == "model_architecture":
            return True
        raw = source.raw
        return isinstance(raw, str) and raw.strip().lower().startswith("modelarch:")

    def ingest(self, source: Source, ctx: IngestContext) -> Document:
        raw = str(source.raw)
        query = raw.split(":", 1)[1].strip() if ":" in raw else raw
        fn = self._match(query)
        dims = _dims_from_name(query, ctx)
        spec = fn(dims)
        return build(spec)

    @staticmethod
    def _match(query: str) -> TemplateFn:
        key = _normalize(query)
        if key in TEMPLATES:
            return TEMPLATES[key]
        for tk, fn in TEMPLATES.items():        # substring fallback (e.g. "gpt2-medium" -> gpt2)
            if tk in key or key in tk:
                return fn
        return _gpt2                            # safe default; LLM extraction is a future enhancement

