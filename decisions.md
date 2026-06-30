# Loupe — Decisions (ADR log)

> Rationale/history for Loupe. Handoff (`handoff.md`) holds current state; `architecture.md` is the
> normative spec the code conforms to. Anchors are immutable; when superseded, keep the anchor token.
> LP-001..LP-008 were ported from the original handoff §4; LP-009+ are added during scaffolding.

---

## [LP-001] Personal tool first, product later
- Date: 2026-06-23
- Status: accepted
- Context: Risk of "framework for everything = framework for nothing."
- Decision: Build a personal tool first; sharing/product comes only if it proves nice in real use. No
  plugin SDK / public API up front.
- Rationale: Generality must be earned by real use, not speculated.
- Consequences: Keep surface area small; resist premature abstraction (YAGNI/AHA).

## [LP-002] Universal scope via shell/lens split
- Date: 2026-06-23
- Status: accepted
- Context: Owner wants max universality (rocket engine → brain signals → books → papers).
- Decision: Achieve universality through the §3 shell/lens split, not a mega-renderer.
- Rationale: A rocket engine, a brain recording, and a book share nothing at the payload level but share
  containment hierarchy + typed relations + semantic zoom. Universality at the structure level; quality
  at the payload level.
- Consequences: The shell is the core; lenses are pluggable per payload type.

## [LP-003] Native, not web
- Date: 2026-06-23
- Status: accepted
- Context: Web is the wrong ceiling for CAD meshes + connectomes + cross-scale zoom.
- Decision: Build native.
- Rationale: Quality/efficiency/tactility. Building for myself ≠ compromise.
- Consequences: Pick a native engine (see LP-004).

## [LP-004] Engine = Godot 4
- Date: 2026-06-23
- Status: accepted
- Options considered:
  - Godot 4 — pro: built-in OpenXR (free VR/AR path), friendly shader pipeline, fast time-to-feel,
    native Vulkan; con: GDScript perf ceiling for heavy loops.
  - Bevy (Rust ECS) — pro: cleanest ECS↔IR mapping, native perf; con: Rust compile loop = slow
    time-to-feel, hand-build XR/UI plumbing.
  - raw wgpu / custom — pro: max control; con: max effort.
  - Unity — pro: most mature XR ecosystem, C# tooling; con: install/licensing weight, stylized
    holographic look is more friction, governance trust risk.
  - Unreal 5 — con: built for photoreal (LP-006 rejects that), C++ kills time-to-feel.
- Decision: Godot 4. Reconsider Bevy only if ECS purity > time-to-feel.
- Rationale: Uniquely satisfies all of {native quality, holographic shader freedom, time-to-feel,
  built-in XR path, desktop-first} at once. Engine question stress-tested again at scaffold time; stands.
- Consequences: Scene-graph (not ECS) — which matches the containment hierarchy directly.

## [LP-005] Desktop-first, XR a first-class future path
- Date: 2026-06-23
- Status: accepted
- Decision: Desktop now; VR goggles / AR glasses are an intended future, not an afterthought.
- Consequences: Drives the intent-bus invariant (LP-007).

## [LP-006] Visual target = med-high HOLOGRAPHIC, not photoreal
- Date: 2026-06-23
- Status: accepted
- Decision: Translucent + emissive glow + rim/fresnel + depth fog; restrained Tron/JARVIS palette; crisp
  in-scene typography.
- Rationale: Cheaper + clearer + scalable than PBR, and matches owner taste. The constraint is a feature.
- Consequences: A shared holographic material; rules out photoreal engines (Unreal).

## [LP-007] Input invariant: object reacts to abstract INTENTS, never raw mouse
- Date: 2026-06-23
- Status: accepted
- Decision: `Input adapter → Intent (Grab/Rotate/Explode/Zoom/Inspect) → Stage`.
- Rationale: This is THE seam that makes XR a "new adapter," not a rewrite.
- Consequences: Desktop mouse is just the first adapter; XR controllers/hands emit the same intents.
  The intent bus is sacred from commit #1.

## [LP-008] "Hold in my hands" = direct object manipulation
- Date: 2026-06-23
- Status: accepted
- Decision: Arcball + inertia + spring-loaded explode, input-device-agnostic.
- Consequences: Device swappable (mouse → webcam hands → XR) behind the intent bus.

## [LP-009] Language = typed GDScript for v0
- Date: 2026-06-23
- Status: accepted
- Context: Open question from handoff §10/§11 (GDScript vs C#). Forcing function: which Godot edition to
  install and what iteration loop to commit to.
- Options considered:
  - Typed GDScript — pros: best time-to-feel (hot-reload, no compile), zero install friction (no .NET
    SDK), GDScript-first shader/scene ecosystem, optional static typing covers most safety. cons: perf
    ceiling on heavy loops (defer to GDExtension), weaker than C# typing (no generics).
  - C# (.NET) — pros: real static typing/generics/refactors, faster hot loops. cons: requires .NET SDK
    + Godot Mono install (machine had runtime but NO SDK), compile cycle slows iteration, most examples
    need translation.
- Decision: Typed GDScript for v0.
- Rationale: The v0 gate (§8) is perceptual (does one shell explode a mesh AND a paper convincingly?),
  won on shader/interaction feel where hot-reload is strongest and compile cycles hurt most. C#'s win
  (refactor safety at scale) is a production concern that only bites after the thesis is proven. IR/lens
  contracts are language-agnostic, so a later C#/GDExtension port of hot paths stays cheap.
- Consequences: Install Godot 4.7 standard (non-Mono). Use static typing throughout. Revisit at the
  production boundary if perf (R3 layout, large point clouds) or refactor pain demands it.
- Links: handoff §10 (RISK: GDScript-vs-C#), §11.2.

## [LP-010] IR is USD-*inspired*, not USD-runtime-backed
- Date: 2026-06-23
- Status: accepted
- Context: §6 IR design + R4 (Mark I→II diff/morph) is the differentiator. OpenUSD already solves
  hierarchy + references + deferred payloads + composition/layers/variants.
- Options considered:
  - Adopt USD runtime — pro: battle-tested composition; con: heavy dependency, GPU/tooling weight,
    against the lightweight personal-tool ethos.
  - USD-*inspired* custom IR — pro: borrow the composition/layer model (maps onto R4 Mark I→II as
    layered opinion-overrides) and the payload-ref/deferred-load model (§6 inline-vs-ref), no heavy dep;
    con: we re-implement a slice of composition ourselves.
- Decision: Make `loupe-ir/v1` USD-inspired; no USD runtime dependency.
- Rationale: Gets the hardest differentiator (R4) as a near-native concept (two layers over one base)
  without coupling to a heavy runtime. Engine-independent.
- Consequences: v1 schema ships now WITHOUT layer composition (single-doc), but reserves the seam:
  versioned `loupe-ir/v1`, payload `data` inline OR `ref`, provenance on every entity. R4 layering is a
  v2 extension over the same Entity model.
- Links: handoff §6, §7 R4.

## [LP-011] Pull the Ingestor layer forward; first ingestor = blueprint→IR (procedural)
- Date: 2026-06-23
- Status: accepted
- Context: v0 primitives don't read as a real rocket engine. Owner wants real, per-part geometry that
  still fully explodes. Forcing function: how to get recognizable per-part geometry without sourcing a
  cleanly-split CAD model (verified rare/CC0-unfriendly — NASA models are public-domain but grouped/OBJ,
  needing manual Blender splitting).
- Options considered:
  - Source a per-part CC0 glTF — pro: true CAD fidelity; con: such clean per-part models are rare;
    requires manual Blender splitting; sourcing is the bottleneck, not the engineering.
  - Whole-engine single mesh — pro: easy; con: one mesh can't sub-explode (kills the thesis for that
    sample).
  - Blueprint→IR procedural ingestor + parametric geometry (revolve/tube) — pro: each part is its own
    entity → FULL explode; the bell-nozzle revolve makes it read as a real engine; zero external assets;
    universal (a blueprint is just another ingestor; revolve/tube are generic CAD primitives); this IS
    the architecture's planned Ingestor layer, brought forward; the ingestor holds domain math (compute
    a bell profile from throat/exit radius + length) so it's a real adapter, not a 1:1 rename. con:
    more geometry + ingestor code; not photoreal.
- Decision: Build the Ingestor layer now. First ingestor = a blueprint→IR procedural adapter. Add
  surface-of-revolution + tube geometry to the mesh lens. Keep a glTF `ref` loader so a real model
  drops in when available (and a future glTF ingestor can auto-split multi-node models for per-part
  explode).
- Rationale: Delivers "real-looking, per-part, fully explodable" now without the sourcing bottleneck,
  while exercising the universal adapter seam the project always planned (handoff §5 Ingestors,
  architecture "Future work"). Domain knowledge lives in the ingestor; the lens stays generic
  (renders revolve/tube/ref); the IR stays declarative.
- Consequences: New layer `src/ingest/` + `blueprints/`. mesh lens gains `revolve`/`tube` shapes and
  `payload.ref` glTF/scene loading with holographic material override. main ingests the rocket sample
  live from a blueprint. Opens the door to more ingestors (glTF, code, papers) on the same seam.
- Links: handoff §5 (Ingestors row), architecture.md Ingestor layer; LP-002 (shell/lens split),
  LP-006 (holographic override on real meshes).

## [LP-012] The universal function = a standalone, Copilot/engine-independent Python package
- Date: 2026-06-23
- Status: accepted
- Context: Universality is the project's scope: `visualize(something) → function(something) → loupe IR`,
  for ANYTHING (rocket engine, transformer/LLM, book, brain, codebase), including things that must be
  web-scraped. Owner constraints: (a) it must NOT live inside Copilot (no lock-in; needs independence),
  (b) token count must stay minimal, (c) it is a function, not a persona.
- Options considered:
  - Copilot skill as the core — pro: easy to invoke in Copilot; con: LOCK-IN, not independent (rejected
    by constraint a).
  - Agent owns ingestion — pro: handles vague inputs; con: nondeterministic, token-heavy, hard to treat
    as a reproducible `function` (rejected as the core; kept as optional wrapper).
  - In-engine GDScript ingestion — pro: one runtime; con: can't web-scrape / call torch / call LLMs
    well; couples ingestion to the engine (rejected).
  - Standalone Python package (lib + CLI) emitting loupe-ir/v1 — pro: independent of Copilot AND engine;
    can scrape + introspect torch + parse ASTs + call LLMs; testable, cacheable, reproducible; one
    artifact callable by the engine, an agent, a Copilot-skill wrapper, the CLI, or tests. con: a second
    language/runtime alongside Godot (acceptable — they meet only at the IR file).
- Decision: Build `loupe-ingest`, a standalone Python package (library API `ingest(source)->IR`,
  `expand(node)->children`; plus a CLI). It depends on neither Copilot nor the engine. The Godot engine
  ONLY ever loads IR. Skill/agent are optional thin wrappers around the package, never the core.
- Rationale: A skill IS a function and an agent is a worker that calls functions — so the universal
  function is the package; the agent is an optional driver for vague inputs. Independence + token
  constraints both point to a self-contained, deterministic-first library.
- Consequences: New `ingest/` package (with a `.gdignore` so Godot skips it). The prototype GDScript
  `BlueprintIngestor` MOVES to Python; the engine keeps only the geometry renderer (`proc_mesh.gd`).
  Python computes "what is it" (incl. bell-nozzle profile numbers); Godot draws it.
- Links: LP-011 (Ingestor layer), LP-013; mirrors AI-Evals/AgentSuite "independent core + orbiters".

## [LP-013] Deterministic-first, token-frugal pipeline with a provider-agnostic LLM client
- Date: 2026-06-23
- Status: accepted
- Context: The pipeline must minimize tokens and run $0/offline-capable, yet stay universal (read
  unstructured/unknown inputs). The LLM must be swappable across GPT/Sonnet/Gemini/Ollama.
- Options considered:
  - Pure deterministic per-domain — pro: 0 tokens, exact; con: not universal (can't read arbitrary
    unstructured input).
  - Pure LLM compiler — pro: maximally universal; con: token-heavy, nondeterministic, hallucination risk.
  - Hybrid: deterministic-first, LLM only at the frontier — pro: 0 tokens on structured sources, LLM
    only when structure can't be derived; con: more code paths.
- Decision: Hybrid. Try deterministic extractors first (config.json, AST, glTF nodes, Wikipedia
  API/infobox, CAD → 0 tokens). Fall back to a grounded LLM ONLY when structure can't be derived.
  Token-frugality is a hard rule: cache-by-input-hash (re-runs = 0 tokens, reproducible), lazy
  expansion (only pay to expand the node you zoom into), compact prompts + structured/JSON-constrained
  output + bounded max_tokens, and a local-model (Ollama) option for $0/offline. Every LLM-built entity
  carries provenance (model+temp+prompt-version) and a source citation; prefer authoritative structured
  sources to resist hallucination.
- Decision (LLM client): one provider-agnostic `LLMClient` interface with a factory over backends
  OpenAI (gpt) / Anthropic (sonnet) / Google (gemini) / Ollama (local). Providers are LAZY-IMPORTED so
  the package needs ZERO LLM dependencies unless a provider is actually used; LLM is OFF by default.
- Rationale: Universality without paying for it on the common (structured) path; reproducibility +
  $0/offline capability; freedom to swap models per task/cost.
- Consequences: `llm/{client,providers}.py`, `cache.py`, `provenance.py`; deterministic ingestors are
  the default path. A mock provider enables fully-offline tests (0 tokens).
- Links: LP-012; owner reproducibility/provenance + $0-prototype doctrines.

## [LP-014] Data contract + per-domain API ingestor strategy; payload set incl. `volume`
- Date: 2026-06-23
- Status: accepted
- Context: Owner reframed universality as "ask for the data each domain needs; if insufficient, the
  `something` function generates more." Needed a curated menu of domains → required data → formats →
  open sources → Loupe payload, to drive ingestor design rather than ad-hoc rendering.
- Decision: Maintain `docs/data-contract.md` as the living input spec across 15 domain families
  (mechanical, electronics, architecture, software, ML, research, neuro, molecular, chemistry, physics,
  earth, business, math, medical, media). Each renderable input maps to a payload type drawn by a lens;
  universal structure (hierarchy + relations) is always present. Add `volume` to the payload set (for
  DICOM/NIfTI/NetCDF fields). Acquisition is tiered: deterministic/open-API first ($0), LLM frontier
  fallback, and a `Gen` (synthesis) arm for missing renderable data.
- Rationale: `graph` + `mesh` cover most domains; +`matrix`/`signal`/`point_cloud`/`volume` ≈ complete.
  A large fraction of data is deterministically scrapable via open APIs (arXiv, S2, Wikidata, PDB,
  AlphaFold, PubChem, Allen Brain, HCP, JPL Horizons, USGS, HF Hub, GitHub) → universality without
  per-call tokens.
- Consequences: Build order that unlocks the most domains fastest:
  `graph → mesh/ref → matrix → signal → point_cloud → volume`, each paired with a per-domain ingestor.
  The "actual parts, universally" requirement is met by the right LENS per payload (not one geometry
  engine): mechanical→mesh, transformer→matrix/graph, brain→signal/graph. Missing data (e.g. attention
  maps from a bare config) is produced by the Gen/synthesis pass.
- Links: docs/data-contract.md; LP-002 (shell/lens split), LP-013 (deterministic-first + Gen).

## [LP-015] First real per-domain API ingestors (arXiv, PDB, GitHub) + graph lens
- Date: 2026-06-23
- Status: accepted
- Context: Prove the universal-function loop on REAL web data, not hand-authored files, across multiple
  domains from the data contract (LP-014).
- Decision: Ship three deterministic ($0) API ingestors and the first data lens:
  - `arxiv` — arXiv Atom API (metadata) + best-effort HTML section scrape → paper hierarchy (`text`).
  - `pdb` — RCSB `.pdb` download → structure→chains hierarchy; each chain a `graph` payload of the real
    Cα backbone (true 3D atomic coordinates + peptide bonds).
  - `github` — public git-tree API → directory/file containment hierarchy (`text`).
  - `graph` lens (`src/lens/graph_lens.gd`) — nodes (MultiMesh spheres) + edges (line mesh), auto
    centered/scaled; serves PDB/connectome/molecule/code graphs.
  Source conventions: `arxiv:<id>`/arxiv URL, `pdb:<4-char id>`, `github:owner/repo`/github URL; the
  router claims by prefix/kind_hint (deterministic before LLM).
- Rationale: Two of three render with EXISTING lenses (arXiv/GitHub = hierarchy+text); only PDB needed a
  new lens — confirming "actual parts, universally" is achieved by the right LENS per payload, not one
  geometry engine. All $0, deterministic, cached, reproducible.
- Consequences: 18 pytest pass (offline parse/routing). Live round-trip verified: CLI hit real APIs →
  arXiv (12 ent, real sections), PDB 1CRN (real Cα graph), GitHub flask (288 files) → Godot loads all
  (`RESULT PASS`) and renders (screenshots). Engine keys 4/5/6. Next contract-driven ingestors:
  Semantic Scholar/Wikidata (`graph`), HF Hub, then `matrix`/`signal` lenses.
- Links: docs/data-contract.md (§4,5,6,7), LP-014; src/lens/graph_lens.gd; ingestors/{arxiv,pdb,github}.py.

## [LP-016] `matrix` lens — holographic heatmap with a faithful path and an honest schematic path
- Date: 2026-06-26
- Status: accepted
- Context: Next on the build order (LP-014: graph→mesh→**matrix**→signal→…). The transformer ingestor
  already emits 50 `matrix` payloads (embeddings, LM head, per-head attention) that fell back to grey
  markers, so the matrix lens unlocks ML/neuro/chemistry coverage with zero new ingestor work.
- Options considered:
  - Fabricate plausible values when a source only knows dimensions (e.g. a bare HF config knows
    50257×512 but holds no weights) — rejected: violates the provenance/honesty doctrine (would render
    invented "weights" indistinguishable from real ones).
  - Skip dimension-only matrices, render only when `values` exist — rejected: loses the common case
    (config-derived architectures) entirely.
  - Two explicit paths: a FAITHFUL heatmap from real `values` (block-averaged to fit, min-max
    normalized), and an HONEST SCHEMATIC grid when only `rows`/`cols`/`square` are known — a decorative
    low-frequency field whose DIMENSIONS are true but whose cells encode no data, labelled
    "(schematic)". — chosen.
- Decision: Ship `src/lens/matrix_lens.gd` (payload type `matrix`). One vertex-colored additive mesh
  (two tris/cell) → a holographic heatmap; dark→accent→white ramp with value-driven alpha. Capped at
  `_MAX_SIDE`=28 cells/axis (giant matrices block-downsample); aspect clamped to `_MAX_ASPECT`=6:1 so a
  50257×512 matrix is a legible strip, not a 1px line. The label ALWAYS reports the TRUE dimensions and
  appends "(schematic)" when no real values were supplied.
- Rationale: Keeps the shell untouched (registry-only registration, LP-002), renders the existing
  transformer sample's 82 entities fully, and preserves the reproducibility/honesty bar — a viewer can
  never mistake a dimension-only placeholder for real weights.
- Consequences: `MatrixLens` registered in `lens_registry.gd`. New sample `ir/samples/matrix_demo.loupe.json`
  (real causal-attention 12×12 + correlation 16×16 + schematic 50257×512 embedding), engine key **7**.
  `tools/verify.gd` now also RENDERS every entity through the registry headless (catches lens
  compile/runtime errors, not just IR parse) — all 7 samples `RESULT PASS`, 18 pytest still pass. Next:
  `signal` lens (training curves, spike trains, EEG, audio), then R4 Mark I→II morph.
- Links: docs/data-contract.md (§5,7,15), LP-014, LP-002 (shell/lens split), LP-013 (provenance/honesty);
  src/lens/matrix_lens.gd; ir/samples/matrix_demo.loupe.json; tools/verify.gd.


## [LP-017] "transformer" config-decomposer → universal "Model Architecture" arm
- Date: 2026-06-29
- Status: accepted
- Context: Owner: nail one arm at a time; first = model architecture. Must feel REAL — see self-attention compute, LSTM gates/states, ResNet layers/params — hold it, drill across abstraction levels. Web-first, LLM minimized, ONE adapter per arm.
- Decision: Reframe arm as data-flow SYSTEM diagrams across abstraction levels. One universal model_architecture adapter (families = templates inside, real dims from web/HF config, LLM gap-fill only). Dedicated dataflow + mechanism lenses. Exemplar first: transformer self-attention.
- Rationale: Faithful + tactile differentiator; arm-level adapter generalizes point 4; templates keep LLM near-zero, preserve LP-013 honesty.
- Consequences: old transformer.py folds into model_architecture; new attention/dataflow lenses; expand ViT/ResNet/CNN/GRU/SD as templates. Build order in plan.md.
- Links: plan.md; LP-013, LP-016, LP-002; ingestors/transformer.py.

## [LP-018] `attention` lens — self-attention shown computing (depth exemplar)
- Date: 2026-06-29
- Status: accepted
- Context: Realism: must SEE Q/K/V→QKᵀ→softmax→·V, not a static box. Honesty: dims real; activations illustrative (labelled), no fabricated weights as real.
- Decision: payload type `attention`; lens animates token lanes → Q·Kᵀ score grid → softmax row weighting → value mixing, real d_model/heads/seq labelled, illustrative tag. Mechanism Node3D self-animates via _process.
- Consequences: AttentionLens registered; sample model_attention; engine+verify key 8. Next: dataflow lens.
- Links: plan.md; src/lens/attention_lens.gd; LP-016 (faithful vs illustrative split).

## [LP-019] Focus-dive navigation: depth-stacked layers (parent recedes on Z)
- Date: 2026-06-29
- Status: accepted
- Context: Showing all levels = clutter; explode-spread + fade still overlapped. Owner wants engine-cutaway feel: see internals, parent stacked behind on orthogonal axis, visible on rotate.
- Decision: click/E dives into a part; the focus card hides, only its children render at the front plane; ancestor chain recedes along -Z (visible when rotated); siblings hidden; Q ascends. Camera auto-frames children. Hidden parts disable picking. Click=inspect+dive, right-drag=pan, drag=rotate.
- Consequences: Stage._set_focus state machine (2=solid,1=ghost-behind,3=focus-hidden,0=hidden) + z offsets; EntityNode.set_focus_state(state,z). NOTE: never hide an ancestor node (collapses subtree) — recede, don't hide. 8 samples PASS.
- Links: src/stage/stage.gd, entity_node.gd, src/input/desktop_input_adapter.gd; LP-018, LP-007.

## [LP-020] Model-architecture exemplar UX locked (transformer)
- Date: 2026-06-29
- Status: accepted
- Context: Iterated the transformer arm to "good result": engine-dive nav + paper-faithful internals.
- Decision: Depth-stacked focus-dive; click/E dive, Q ascend, R recenter, C panel; flow = spotlight (active part brightens, no lines); per-component LaTeX label below each part (PNG via tools/render_equations.py); right panel bullets per click; L2 = Vaswani Fig-2 MHA (Linear QKV top -> 12 stacked SDPA heads on z, function-named -> Concat -> W_O bottom). UI: title+meta TL, MODELS menu, legend BL.
- Consequences: lenses attention/matrix/text/equation all show eqn-below; sample model_attention 23 ent; pattern reusable for all models. 8 samples PASS. Next: expand to more architectures via templates.
- Links: src/lens/*, src/stage/stage.gd, src/main/main.gd, tools/render_equations.py.

## [LP-021] Expanded model arm: AlexNet, LSTM, Stable Diffusion, Mamba
- Date: 2026-06-29
- Status: accepted
- Context: Owner approved 4 new architectures via LP-020 template (one per family).
- Decision: Hand-authored samples (alexnet/lstm/stable_diffusion/mamba) with L0->dive internals, per-part LaTeX, named sub-blocks. New eqns rendered (conv/pool/fc, lstm gates, clip/unet/vae/diffuse, ssm/mamba_gate). Engine keys 9/0/F/G; 12 samples PASS.
- Links: ir/samples/{alexnet,lstm,stable_diffusion,mamba}.loupe.json; tools/render_equations.py; src/main/main.gd.

## [LP-022] Universal model-architecture adapter (one adapter per arm)
- Date: 2026-06-29
- Status: accepted
- Context: Expand the model arm to arbitrary models without hand-authoring each IR (owner: "make an adapter using this data").
- Decision: ingest/loupe_ingest/ingestors/model_arch.py — a declarative ModelSpec->IR compiler (build()) encoding the locked UX (LP-020): stages laid row/stack(z), per-part eqn id, sequential flow wiring, dive internals as lod_band-2 children. Template library (gpt2/transformer, alexnet/cnn, lstm/rnn/gru, stable_diffusion/sd, mamba/ssm, resnet, vit) keyed by normalized name w/ substring fallback. Deterministic/$0; web-first dims hook (ctx.options['config'] = HF config); LLM is future gap-filler only. Source form `modelarch:<name>`; routed first (deterministic).
- Consequences: add a model = add one builder (data, no engine change). resnet+vit generated by adapter render in-engine (keys H/J); 31 pytest pass; 14 engine samples PASS. CLI: loupe-ingest "modelarch:resnet" -o out.
- Links: ingest/loupe_ingest/ingestors/model_arch.py; tests/test_model_arch.py; router.py; ir.py (PAYLOAD_TYPES += attention,conv); LP-020/LP-021.

## [LP-023] Adapter finalized (web-first dims, catalog) + expanded to 14 models
- Date: 2026-06-29
- Status: accepted
- Context: "finalize the adapter properly then use that to expand."
- Decision: (1) Web-first dims: ModelArchIngestor fetches real HuggingFace config.json (acquire.hf_config, public/no-key, cached, opt-out offline=True) -> faithful n_layers/n_heads/d_model (verified distilgpt2=6L, gpt2-medium=24L/16H/1024). Falls back to family defaults offline. LLM still future-only. (2) tools/gen_models.py emits every template to ir/samples/gen/<name>.loupe.json + catalog.json (adapter = single source of truth). Engine cycles the catalog with [ and ]. (3) Expanded templates to 14: +bert, gru, vae, gan, moe, unet, seq2seq (enc-dec cross-attn). New eqns rendered.
- Consequences: 38 pytest pass; engine verify renders all 14 generated + hand-authored (RESULT PASS). Add a model = one builder -> appears in catalog automatically. CLI: loupe-ingest "modelarch:gpt2-medium".
- Links: ingest/.../model_arch.py, acquire/__init__.py (hf_config), tools/gen_models.py, ir/samples/gen/catalog.json; LP-020/021/022.

## [LP-024] L2/L3 nesting + per-arm dropdown menus
- Date: 2026-06-29
- Status: accepted
- Context: Some L2s crammed a wide mechanism beside its heads; UI needed per-arm navigation.
- Decision: (1) Compiler recursion (_emit_parts): a mechanism stage's sub-parts become the mechanism's OWN children, so L2 = just the mechanism (clean), L3 = sub-parts; many homogeneous heads auto z-stack (MHA look). Structure: model -> stage card (L1) -> mechanism (L2) -> heads/parts (L3). (2) Per-arm OptionButton dropdowns across the top (Model Architecture [from adapter catalog] · Mechanical · Documents · Biology · Code · Data); selecting loads the sample. Catalog loaded before HUD.
- Consequences: 38 pytest pass; all samples RESULT PASS; vit/bert/moe/seq2seq L2 clean, heads at L3.
- Links: ingest/.../model_arch.py (_emit_parts, Part.children); src/main/main.gd (_build_arm_menus).
