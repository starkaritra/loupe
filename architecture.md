# Loupe — Architecture

Loupe is a native (Godot 4, typed GDScript), desktop-first, holographic, domain-agnostic
**exploded-view explorer**. Point it at any nested system — a rocket engine, a brain recording, a
research paper — and hold, explode, and zoom across scales to inspect detail at any granularity.

The whole design rests on one separation: **a universal SHELL × specialized LENSES.**

- **SHELL (the core, not swappable):** containment hierarchy, semantic zoom / LOD, explode, navigation,
  and direct manipulation. Every target is "nested things you can explode and zoom across scales," so the
  structure is identical for a bolt-in-an-engine and a section-in-a-paper.
- **LENSES (swappable, per payload type):** each node carries a typed payload
  (`mesh | text | signal | image | equation | table | point_cloud | …`); a lens registry dispatches each
  payload to a renderer that knows how to draw *that type* beautifully.

> Universality at the structure level; quality at the payload level.

## Two independent halves, one contract

Loupe is **two standalone programs that meet only at the IR file**:

| | What | Where | Depends on |
|---|---|---|---|
| **`loupe-ingest`** | the *universal function* `anything → loupe-ir/v1` | `ingest/` (Python pkg) | nothing (not Copilot, not the engine) |
| **the engine** | renders/explores an IR document | `src/` (Godot 4, GDScript) | nothing but an IR file |

This split is deliberate: ingestion needs to web-scrape, introspect live models, parse ASTs, and call
LLMs (Python's world); rendering needs to be a fast native holographic app (Godot's world). They never
import each other — the IR contract is the only coupling.

## How to visualize ANYTHING (the recipe)

`visualize(something)` always means: **write/choose an Ingestor that maps `something → IR`.** The engine
never changes. `loupe-ingest` is deterministic-first and token-frugal — structured sources cost **0
tokens**; an LLM is used only at the frontier (see `ingest/README.md`).

```
ingest(something)
   Acquire   (optional: web-scrape / fetch / introspect a live object)
     → Route     pick the most specific ingestor (deterministic first; LLM last)
     → Structure chosen ingestor → IR entities + hierarchy + relations + tiers
     → Validate  schema + referential integrity
     → Stamp     provenance on every entity (source, hash, model, temp, prompt ver)
   → loupe-ir/v1 JSON  →  the engine renders it
```

| Domain | Ingestor / source | Path |
|---|---|---|
| Transformer / LLM | HF `config.json` or live `nn.Module` (`tools/extract_transformer.py`) | deterministic, 0 tokens |
| Mechanical (rocket engine, pump) | engineering blueprint JSON (computes bell-nozzle/chamber geometry) | deterministic, 0 tokens |
| A paper / book / codebase | AST / outline (planned) or the LLM frontier | mixed |
| A bare concept ("a brain connectome") | web-grounded **LLM frontier** (GPT/Sonnet/Gemini/Ollama) | tokens, cached |

Adding a domain = a new `Ingestor` subclass behind the fixed IR contract; the engine is untouched. This
is what makes "works for anything" real rather than aspirational.

## Layers (the engine — data flow, top → down)

| Layer | Swappable? | Code | Responsibility |
|---|---|---|---|
| **IR** — universal structure schema | — (the contract) | `ir/loupe-ir.schema.json`, `src/ir/ir_types.gd` | The one neutral thing everything compiles to (`loupe-ir/v1`). |
| **IR loader** | — | `src/ir/ir_loader.gd` | Parse + validate JSON → typed IR; record/derive provenance. |
| **Stage** — scene builder + controllers | no (the core) | `src/stage/stage.gd`, `lod_controller.gd`, `explode_controller.gd` | Build the Godot scene tree from the IR hierarchy; own LOD and explode. |
| **Lens registry** | — | `src/lens/lens_registry.gd` | Map `payload.type` → a `Lens`. |
| **Lens** | yes, per payload type | `src/lens/lens.gd`, `mesh_lens.gd`, `structure_text_lens.gd`, `graph_lens.gd` | `render(payload, ctx) → Node3D` visuals for one payload type. `mesh` supports primitives, procedural revolve/tube (`stage/proc_mesh.gd`), and real glTF via `ref`; `graph` renders nodes+edges. |
| **Intent bus** — Grab/Rotate/Explode/Zoom/Inspect | — (the invariant) | `src/intent/intent.gd`, `intent_bus.gd` (autoload) | Decouple input from the stage. The XR seam. |
| **Input adapter** | **yes** ← the XR seam | `src/input/desktop_input_adapter.gd` | Translate device input into abstract intents. |
| **Holographic material** | shared | `src/materials/holographic.gdshader` | The med-high holographic look (translucent + emissive + fresnel + depth fog). |
| **Main** | — | `src/main/main.gd`, `main.tscn` | Wire everything; load a sample IR; set up camera/light/env. |

```
 source(s) ──▶ Ingestor* ──▶  IR  ──▶  IR loader ──▶ Stage ──┬─▶ Lens registry ─▶ Lens ─▶ payload visuals
                                                             └─▶ LOD + explode controllers
   desktop input ─▶ Desktop input adapter ─▶ Intent bus ─▶ Stage
   (*ingestors live in the standalone `loupe-ingest` Python package — see "Two independent halves" above)
```

## The IR (`loupe-ir/v1`)

A single JSON document. Schema: `ir/loupe-ir.schema.json`; typed in `src/ir/ir_types.gd`.

```
Document {
  version   : "loupe-ir/v1"
  root      : id
  entities  : [ Entity ]
  relations : [ Relation ]
  lod_policy : LODPolicy
  provenance : Provenance
}
Entity {
  id, label, kind                # kind = domain tag ("part","section","region",…)
  parent        : id | null      # containment hierarchy — the universal backbone
  placement     : {pos, rot, scale} | null   # explicit geometry, OR null → auto-layout
  lod_band      : int            # which zoom depth this appears at (0 = always/top)
  payload       : { type, data | ref }       # type ∈ mesh|text|signal|image|equation|table|point_cloud
  content_tiers : { overview, detail, deep }  # multi-resolution text description
  provenance    : Provenance | null
}
Relation  { from, to, kind }     # flow | depends_on | connects | cites | feeds | …
LODPolicy { bands, distance_thresholds }
Provenance { source, hash, generated_at, generator }
```

Rules: versioned schema; payload `data` inline OR `ref` to a file/stream (large signals are not inlined);
every document and entity carries provenance.

## The intent invariant (the XR door)

The stage never sees raw mouse events. Input adapters translate device input into a small fixed set of
intents — `GRAB, RELEASE, ROTATE, PAN, ZOOM, EXPLODE, COLLAPSE, INSPECT, SELECT` — emitted on the
`IntentBus` autoload. The stage subscribes and reacts. Adding XR later is "another input adapter that
emits the same intents," never a rewrite.

## Semantic zoom / LOD

The LOD controller reads camera distance against `LODPolicy.distance_thresholds` to compute a current
"depth," then shows/hides entities by `lod_band` and swaps each entity's content tier
(`overview → detail → deep`). Explode is a separate axis: the explode controller springs each child from
its collapsed home position to a radial exploded offset based on an explode factor in `[0,1]`.

## Holographic material (the look)

A single Godot spatial shader: translucent surface, emissive fill, view-dependent rim/fresnel glow,
restrained Tron/JARVIS palette, depth fog. Per-entity tint and glow are set as shader params so a lens
can theme its visuals while staying coherent.

## Future work (v2)

- **More ingestors** in `loupe-ingest`: code/AST → IR, paper/book outline → IR, brain/connectome → IR.
- **Lazy expansion** — `expand(node)` so deep cross-scale zoom (R1) builds subtrees on demand instead of
  pre-materializing a whole brain; the same ingestors serve it, the engine calls back at runtime.
- **`matrix`/`signal`/`volume` lenses** — render attention maps, weight tensors, waveforms, and scalar
  fields natively (transformer IR already emits `matrix` payloads; today they fall back to the marker
  lens). The `graph` lens exists and renders nodes+edges (PDB backbones, connectomes, molecules, code).
- **R3 — auto-layout** of structure with no geometry (3D force-directed + domain hints) — v0 uses
  explicit `placement` for mesh and simple hierarchical layout for structure.
- **R4 — Mark I → II refine/diff/morph:** load two IR layers over one base and watch components get
  replaced/optimized. The IR (LP-010) reserves the composition seam for this.
- **XR viewpoint/display** (OpenXR stereo) via a new input adapter on the same intent bus.
