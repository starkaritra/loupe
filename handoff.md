# Loupe — Handoff *(provisional codename)*

> **Status:** **v0 vertical slice SCAFFOLDED & verified headless.** Godot 4.7 project builds; both
> opposite-domain samples load through the full pipeline. This doc is the pickup point.
> **Owner:** Aritra Das · **Created:** 2026-06-23 · **Location:** `C:\Code\Self\projects\loupe\`

> ### Model Architecture arm — exemplar built (2026-06-29)
> **Universal adapter finalized (LP-022/023).** The arm now expands via ONE adapter
> `ingest/loupe_ingest/ingestors/model_arch.py`: a declarative `ModelSpec→IR` compiler encoding the
> locked UX, a 14-model template library (gpt2, bert, seq2seq, vit, alexnet, resnet, unet, lstm, gru,
> mamba, stable_diffusion, vae, gan, moe), **web-first dims** (fetches real HuggingFace `config.json`,
> cached, `offline=True` to skip; verified distilgpt2=6L, gpt2-medium=24L). Generate all via
> `python tools/gen_models.py` → `ir/samples/gen/*.loupe.json` + `catalog.json`; engine cycles them with
> **[ and ]**. Add a model = add one builder. CLI `loupe-ingest "modelarch:<name>"`. 38 pytest pass.
> Hand-authored flagship `model_attention` (12-head Fig-2 MHA) stays as the showcase exemplar.
> Arm #1 pivot (LP-017): the old transformer config-decomposer becomes a universal **Model Architecture**
> arm — data-flow system diagrams across abstraction levels, one universal adapter per arm, web-first +
> LLM-minimized. Engine now navigates like opening a machine: **click = dive INTO a part** (its outer
> casing + siblings fade, internals reveal), **right-drag = move**, **Q/E = back out**; click shows a name
> + zoom-deepening explanation panel; data flow is **animated pulses** (not arrows). Depth exemplar
> (LP-018): the `attention` lens shows self-attention computing; sample drills model→block→**12 heads**.
> Engine key 8. 8 samples `RESULT PASS`. **Next:** universal `model_architecture` adapter, then ViT/ResNet/GRU/SD.: the old transformer config-decomposer becomes a universal **Model Architecture**
> arm — data-flow system diagrams across abstraction levels, one universal adapter per arm, web-first +
> LLM-minimized. First depth exemplar (LP-018): a new **`attention` lens** (`src/lens/attention_lens.gd`)
> that shows self-attention *computing*: query/value token lanes, an 8×8 Q·Kᵀ score grid, a softmax row
> that sweeps query-by-query, value tokens brightening by weight, an output token mixing — real dims
> labelled, dynamics tagged illustrative (LP-013 honesty). Sample `ir/samples/model_attention.loupe.json`,
> **engine key 8**. 8 samples `RESULT PASS`. **Next:** dataflow lens (model-level boxes/arrows/LOD), then
> the universal `model_architecture` adapter (name→family template+real dims), then ViT/ResNet/GRU/SD.

> ### `matrix` lens — built (2026-06-26)
> The next lens on the build order (graph→mesh→**matrix**→signal) ships as `src/lens/matrix_lens.gd`
> (LP-016): a holographic heatmap (one additive vertex-colored mesh) with **two honest paths** — a
> **faithful** render of real `values` (block-averaged to ≤28²/axis, min-max normalized) and an
> **honest schematic** grid when only `rows`/`cols` are known (true dimensions, decorative cells,
> labelled "(schematic)") — so a dimension-only placeholder is never mistaken for real weights
> (LP-013 provenance bar). Extreme aspects clamped to 6:1 (a 50257×512 embedding reads as a legible
> strip). This instantly upgrades the **transformer** sample's 50 matrix payloads from grey markers to
> real heatmaps — **zero new ingestor work**. New sample `ir/samples/matrix_demo.loupe.json` (real
> 12×12 causal attention + 16×16 correlation + schematic 50257×512 embedding), **engine key 7**.
> `tools/verify.gd` now also RENDERS every entity through the registry headless (catches lens
> compile/runtime errors, not just IR parse): **7 samples `RESULT PASS`**, **18 pytest pass**, visual
> screenshot confirmed.
> **Next:** `signal` lens (training curves / spike trains / EEG / audio), then R4 Mark I→II morph.


> ### Real per-domain API ingestors + graph lens — built (2026-06-23)
> Three deterministic ($0) web-API ingestors prove the universal loop on REAL data (LP-015):
> `arxiv` (arXiv API + HTML sections → paper), `pdb` (RCSB → real Cα backbone as `graph`), `github`
> (git-tree → dir/file hierarchy). New **graph lens** (`src/lens/graph_lens.gd`, MultiMesh nodes + line
> edges) renders PDB atoms/bonds, connectomes, molecules, code graphs. **18 pytest pass**; live
> round-trip verified (CLI→APIs→Godot, `RESULT PASS`, screenshots). Engine keys **4** arXiv · **5**
> protein · **6** github. Source forms: `arxiv:<id>`, `pdb:<4char>`, `github:owner/repo`.
> Catalog of domains→data→formats→sources→payload in **docs/data-contract.md** (LP-014); `volume`
> payload added to the IR contract.
>
> **Generate (live):** `cd ingest; loupe-ingest "pdb:4HHB" -o ..\ir\samples\protein.loupe.json` ·
> `loupe-ingest "arxiv:2407.12844" -o ...` · `loupe-ingest "github:owner/repo" -o ...`.
> **Next:** more contract ingestors (Semantic Scholar/Wikidata graph, HF Hub) + `matrix`/`signal` lenses.

> ### Universal ingest layer — built (2026-06-23)
> The **universal function** `visualize(something) → loupe-ir/v1` is a **standalone Python package**
> `ingest/loupe_ingest/` (LP-012), independent of Copilot AND the engine; the engine only ever loads IR.
> Deterministic-first + token-frugal (LP-013): structured sources compile with **0 tokens**; the LLM is a
> frontier fallback (off by default) behind a provider-agnostic client — **GPT/Sonnet/Gemini/Ollama**,
> lazy-imported. Cache-by-hash → reproducible, re-runs free. Ingestors: `transformer` (HF config / live
> `nn.Module` via `tools/extract_transformer.py`), `blueprint` (computes bell-nozzle/chamber geometry),
> `llm` (grounded frontier). **13 pytest pass** (`cd ingest && pytest`, fully offline). Round-trip
> verified: CLI emits rocket (6 ent) + transformer (82 ent) IR → Godot loads/validates all three samples
> (`RESULT PASS`). Recipe + per-domain table in `architecture.md` ("How to visualize ANYTHING").
>
> **Generate IR:** `cd ingest; loupe-ingest examples\rocket_engine.blueprint.json -o ..\ir\samples\rocket_engine.loupe.json`
> · transformer: `loupe-ingest examples\gpt2_config.json --kind transformer -o ..\ir\samples\transformer.loupe.json`
> · concept (LLM): `loupe-ingest "a brain connectome" --provider ollama -o out.ir.json`.
> Engine keys: **1** rocket · **2** paper · **3** transformer.
>
> **Next:** `matrix`/`graph`/`signal` lenses (transformer emits these, they fall back to markers now);
> lazy `expand(node)` for deep zoom; more ingestors (code/AST, paper).

> ### v0 slice — built (2026-06-23)
> Engine **Godot 4.7 standard** (winget `GodotEngine.GodotEngine`); language **typed GDScript** (LP-009).
> Layered per §5: IR (`src/ir/`, schema `ir/loupe-ir.schema.json`) → IRLoader (validate + provenance) →
> Stage (`src/stage/`: scene build, `ExplodeController`, `LODController`) → Lens registry + **mesh** and
> **text** lenses (`src/lens/`) → Intent bus autoload (`src/intent/`, LP-007) ← desktop input adapter
> (`src/input/`) → holographic shader (`src/materials/holographic.gdshader`, LP-006). Entry: `src/main/`.
> Two samples: `ir/samples/rocket_engine.loupe.json` (mesh, explicit placement) and `paper.loupe.json`
> (text, auto-layout). Decisions LP-009 (GDScript), LP-010 (USD-inspired IR) added.
>
> **Verify (headless, no GPU):**
> `& "$GODOT" --headless --path . --import` then
> `& "$GODOT" --headless --path . --script res://tools/verify.gd` → `RESULT PASS`.
> `$GODOT` = `…\WinGet\Packages\GodotEngine.GodotEngine_*\Godot_v4.7-stable_win64.exe`.
> **Run (window):** `& "$GODOT" --path .` → keys **1**/**2** switch samples, drag=rotate, wheel=zoom,
> **E**/**Q**=explode/collapse.
>
> **Next:** open in a window to tune the holographic feel (shader untested on GPU); then `signal` lens,
> then R4 Mark I→II morph (IR composition seam reserved by LP-010).

---

## 0. One-liner

A **native, holographic, domain-agnostic "exploded-view" explorer**: point it at *anything* with nested
structure — a rocket engine, a brain connectome, a book, a research paper, a codebase — and you can
**hold it, explode it, and zoom across scales** to inspect detail at any granularity. The Iron Man 1
"Mark I → Mark II" hologram, generalized into a reusable tool.

**The name is provisional.** "Loupe" = a jeweler's precision magnifier (inspect fine detail).
Alternatives floated/usable: **Strata** (scale layers), **Manifold**, **Facet**, **Aperture**. Rename freely.

---

## 1. North star (the only durable directive)

> Make me feel like I'm **holding the thing in my hands** — grab it, pull it apart, zoom from the whole
> object down to a single bolt / spike train / sentence — for **any** kind of system, at **med-high
> holographic** visual quality, **efficiently**, as a **native** app.

Everything below is a snapshot to validate, not gospel. The north star is the only fixed point.

---

## 2. Where this came from (lineage)

It is the **generalization of the `eval_platform/blueprint/` site** (a JARVIS/Tron 3D docs site that
explodes a data pipeline into Classifier → Rater → Consolidator, with camera-distance = level of detail).
That web prototype proved the *interaction* works. Loupe extracts the reusable kernel and rebuilds it
**native + universal + tactile**.

- Blueprint lives at: `C:\Code\3pcxp_evals\eval_project\eval_platform\blueprint\`
  (Three.js single-file; `pipeline.json` = structure, `content_src/*.md` = multi-tier content,
  camera distance = LOD). **That `pipeline.json` is literally the first, trivial instance of Loupe's IR.**
- Pattern-cousin to the owner's other "substrate + plugins" projects (AI-Evals, AgentSuite): a
  **black-box-able core with things orbiting it**.

---

## 3. The core architectural insight (make-or-break)

A rocket engine (meshes), a brain recording (time-series), and a book (prose) share **nothing at the
payload level**. Universality is only possible by splitting:

- **The SHELL is universal** — containment hierarchy + typed relations + semantic zoom/LOD + navigation
  + manipulation. *Every* target is "nested things you can explode and zoom across scales." That
  structure is identical for a bolt-in-an-engine and a section-in-a-paper.
- **The LENSES are specialized** — each node carries a **typed payload**
  (`mesh | signal | text | image | equation | table | point_cloud | …`); a **lens registry** dispatches
  each payload to a renderer that knows how to draw *that type* beautifully.

> **Universality at the structure level; quality at the payload level.** This single separation IS the
> framework, and is the genuinely novel/defensible core (paper/patent potential — judge on its own
> merits, per the owner's AI-Evals doctrine).

---

## 4. Decisions locked so far (ADR-style; expand into `decisions.md` when scaffolding)

| ID | Decision | Rationale |
|---|---|---|
| **LP-001** | **Personal tool first**, product/shareable later ("if it's nice, others can use it too"). | Avoids the "framework for everything = framework for nothing" trap. Generality must be earned by real use, not speculated. **No plugin SDK / public API up front.** |
| **LP-002** | **Universal scope is intended**: must scale rocket engine → brain signals → books → papers. | Owner explicitly wants max universality. Achieved via §3 shell/lens split, NOT by one mega-renderer. |
| **LP-003** | **Native, not web.** Web is the wrong ceiling for CAD meshes + connectomes + cross-scale zoom. | Quality/efficiency/tactility. "Building for myself ≠ compromise; that's when I want highest quality + innovation." |
| **LP-004** | **Engine = Godot 4.** | Built-in **OpenXR** (free VR/AR path, LP-006), friendly shader pipeline for the holographic look, fast iteration to a *tactile* result, native Vulkan, C#/GDScript. Chosen over Bevy (more architecturally pure ECS↔IR, but slower time-to-*feel*) and raw wgpu (max effort). **Reconsider Bevy only if ECS purity > time-to-feel.** |
| **LP-005** | **Desktop-first**, but XR is a **first-class future path** (VR goggles, Meta glasses). | Owner: "desktop only now, but there should be a path to extend for VR/AR." Drives LP-007 (intent bus). |
| **LP-006** | **Visual target = med-high HOLOGRAPHIC, not photoreal.** Translucent + emissive glow + rim/fresnel + depth fog; restrained Tron/JARVIS palette; crisp in-scene typography. | Cheaper + clearer + scalable than PBR, and matches owner's taste. This constraint is a feature, not a limitation. |
| **LP-007** | **Input invariant: the object reacts to abstract INTENTS, never to raw mouse.** `Input adapter → Intent (Grab/Rotate/Explode/Zoom/Inspect) → Stage`. | This is THE seam that makes XR a "new adapter," not a rewrite. Desktop mouse is just the first adapter; XR controllers/hands emit the same intents. |
| **LP-008** | **"Hold in my hands" = direct object manipulation** (arcball + inertia + spring-loaded explode), input-device-agnostic. | Owner: "feel like I'm holding that thing." Device is swappable (mouse → webcam hands → XR) behind the intent bus. |

---

## 5. Architecture (target)

Hard-separated layers — this separation is the whole game:

| Layer | Swappable? | v0 (first slice) |
|---|---|---|
| **IR** — universal structure schema | — (the contract) | JSON/typed schema (see §6) |
| **Ingestors** — `any source → IR` | yes, per domain | start with **ONE** (see §8) |
| **Lens registry** — `payload → scene visuals` | yes, per payload-type | **mesh** lens + **structure/text** lens |
| **Stage** — builds scene, owns LOD + explode | no (the core) | Godot scene-graph + LOD bands |
| **Intent bus** — Grab/Rotate/Explode/Zoom/Inspect | — (the invariant, LP-007) | enum + signal/event bus |
| **Input adapter** — emits intents | **yes** ← the XR seam | desktop mouse/keyboard |
| **Viewpoint/Display** | yes | desktop camera (XR stereo later) |

```
 source(s) ──▶ Ingestor ──▶  IR  ──▶  Stage ──┬─▶ Lens registry ─▶ payload visuals
                                              └─▶ LOD/explode controller
   desktop input ─▶ Input adapter ─▶ Intent bus ─▶ Stage
   (XR controllers/hands  ─▶ another Input adapter ─▶ same Intent bus, later)
```

---

## 6. The IR (Intermediate Representation) — draft schema

The one neutral thing everything compiles to. `blueprint/pipeline.json` is the seed; generalize it:

```
Entity {
  id            : string
  label         : string
  kind          : string            # domain tag (e.g. "module","part","region","section")
  parent        : id | null         # containment hierarchy (the universal backbone)
  placement     : {pos, rot, scale} | null   # explicit geometry, OR null → auto-layout (§7 R3)
  lod_band      : int | range       # which zoom depth this appears at
  payload       : { type, data | ref }   # type ∈ mesh|signal|text|image|equation|table|point_cloud|...
  content_tiers : [ overview, detail, deep ]  # multi-resolution description (cf. blueprint content_src)
  provenance    : { source, hash, generated_at, generator }   # reproducibility bar (owner doctrine)
}
Relation { from: id, to: id, kind: string }   # flow | depends_on | connects | cites | feeds | ...
LODPolicy  { bands, distance_thresholds, what-shows-when }
```

Design rules: versioned schema (`loupe-ir/v1`); payload `data` inline or `ref` to a file/stream (a
connectome's signals shouldn't be inlined); everything carries provenance.

---

## 7. The experimental / innovative bets (where quality + novelty live)

The owner explicitly wants experimental, high-innovation work ("try experimental stuff, if it breaks we
fix"). The real research-grade problems:

1. **R1 — Scale-spanning zoom** ("Powers of Ten," interactive + generic): continuous LOD across *orders
   of magnitude* (whole-engine → one bolt; whole-brain → one spike train). Continuous multi-resolution
   navigation is genuinely hard + publishable.
2. **R2 — Lens registry**: the pluggable payload→renderer system. The reuse engine.
3. **R3 — Auto-layout of structure with no geometry**: a paper/book/codebase has hierarchy but no
   physical coordinates. 3D force-directed + domain hints → *meaningful* placement. Research-grade.
4. **R4 — "Mark I → II" refine/diff/morph**: load two IR versions of the same system, *watch components
   get replaced/removed/optimized* with annotations. The cinematic payload + a distinct feature almost
   no existing viewer has. **This is the differentiator — protect it.**

---

## 8. First vertical slice (the plan when picked up)

Ambitious but provable. Order matters:

1. **Lock the IR (§6)** + a minimal **Lens trait/interface** (one method: `render(payload) → scene nodes`).
2. **Godot shell**: load an IR file → build scene from the hierarchy → **explode + zoom + drill with LOD**,
   driven entirely by the **intent bus** (desktop mouse adapter first). Holographic material (LP-006).
3. **Two DELIBERATELY OPPOSITE lenses** to prove universality in one shot:
   - a **`mesh` lens** (a rocket-part-ish / mechanical assembly), and
   - a **`structure/text` lens** (a research paper or book outline).
   If the *same shell* explores both convincingly → the thesis holds.
4. **Then**: a `signal` lens (brain/connectome), then **R4 refine-morph**.

**Definition of done for the slice:** point Loupe at two hand-authored IR files from opposite domains →
explode/zoom/drill both with the same build, in a holographic style, manipulated as if held. Provenance
recorded. `decisions.md` + this handoff updated.

---

## 9. Prior-art / honest positioning (aim at a real gap)

Not an empty field — don't pretend otherwise:
- **C4 model + Structurizr** — depth tiers for *software*, but 2D diagrams, software-only, no cinematic drill-in.
- **CodeCity / Gource** — 3D code viz, fixed metaphor, not general/refinable.
- **CAD exploded views (SolidWorks etc.)** — domain-locked to mechanical parts.
- **Powers of Ten / scale demos** — fixed, non-interactive, single-dataset.

**The unclaimed wedge:** a *domain-agnostic*, IR-driven, **cinematic exploded-view + refinement** explorer
where you plug any system in via an ingestor. Novelty = **generality × the Mark-I→II refine narrative ×
the cross-scale LOD UX** — not any one alone. (Do a proper prior-art sweep before any paper/patent claim.)

---

## 10. Risks & open questions (retire early)

- **RISK: "universal" → mush.** Mitigation: the §3 shell/lens split + §8 "two opposite lenses" gate. If
  one shell can't credibly do mesh AND text, the thesis is wrong — find out in the slice, cheaply.
- **RISK: Godot 4 churn / C#-vs-GDScript.** Owner accepts experimental breakage. Decide GDScript (fast,
  native) vs C# (typed, owner's strong-typing taste) at scaffold time — **OPEN**.
- **RISK: auto-layout (R3) is a rabbit hole.** Keep v0 to explicit `placement` for mesh + simple
  hierarchical layout for structure; defer force-directed.
- **OPEN: provenance for streaming payloads** (a live connectome) vs static files.
- **OPEN: name** (§0).
- **OPEN: is there a $0 / native-distribution constraint?** (Owner's other projects are $0-hostable
  prototypes — but this is a *native personal tool*, likely exempt. Confirm.)

---

## 11. Pickup checklist (for future-me / coderAS)

1. Re-read this handoff + skim `blueprint/` (`pipeline.json`, `src/App.tsx`, `src/data.ts`) — it's the
   working ancestor of every concept here.
2. Confirm with owner: **name**, **GDScript vs C#**, **Godot version installed?** (Godot was NOT verified
   on PATH this session — check/install first).
3. Scaffold `C:\Code\Self\projects\loupe\` as a Godot 4 project; create `decisions.md` (port §4),
   `architecture.md`, and the IR schema file (§6).
4. Build the §8 slice. Keep the intent bus (LP-007) sacred from commit #1 — it's the XR door.
5. Use `kgraph` to persist the structure as it grows.

---

## 12. Verbatim owner intent (so nuance isn't lost)

- "framework where we blow up components and look at details and granularity … a wrapper for different
  objects, processes, etc. … doesn't have to stay web based. Something like solidworks … that scene in
  Iron Man 1 where tony builds the polished mark II from the bulky mark I."
- "It's for my usage, if it's nice then other people can use it too."
- "my usecase is the most universal as well. make it scalable … rocket engine to brain signals to books
  to papers. and web is not optimal. just because I am building for myself doesn't mean I would
  compromise quality. That's when I need highest quality, innovation. Try experimental stuff, if it
  breaks we fix."
- "I want efficiency + visual clarity. I want to feel like I am holding that thing in my hands. Details
  can be med-high holographic quality."
- "desktop only now, but there should be a path to extend it for VR goggles, meta glasses etc."
