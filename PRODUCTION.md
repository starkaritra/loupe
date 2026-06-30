# From Development to Production — a Lifecycle Guide

This document has two parts:

1. **Generic** — the universal path of taking *any* software product from development to a published,
   maintained release, with diagrams. Domain-agnostic; reuse it for any project.
2. **Loupe-specific** — how those generic steps map onto this repository (a Godot 4.7 desktop app with a
   standalone Python content-generator).

---

# Part 1 — The generic lifecycle

## 1.1 The big picture

```mermaid
flowchart LR
    subgraph DEV["1. Development"]
        A[Code + tests] --> B[Local run]
        B --> C{Tests &<br/>review pass?}
        C -- no --> A
    end
    subgraph REL["2. Release engineering"]
        C -- yes --> D[Version bump<br/>+ tag]
        D --> E[Reproducible build]
        E --> F[Package / installer]
        F --> G[Sign + notarize]
    end
    subgraph PUB["3. Publish"]
        G --> H[Distribution channel]
        H --> I[Users install/run]
    end
    subgraph OPS["4. Maintain"]
        I --> J[Telemetry / crash reports]
        J --> K[Triage issues]
        K --> A
    end
```

The loop is the point: **maintenance feeds back into development.** A product is never "done"; it is
*released* and then *operated*.

## 1.2 Stage gates — what "ready to ship" means

```mermaid
flowchart TD
    A[Feature complete] --> B{Unit + integration<br/>tests green?}
    B -- no --> A
    B -- yes --> C{Smoke test on a<br/>clean machine?}
    C -- no --> A
    C -- yes --> D{Docs + changelog<br/>updated?}
    D -- no --> A
    D -- yes --> E{Version tagged?}
    E -- yes --> F[Build artifact]
```

Each diamond is a **gate**: never skip one to ship faster — skipped gates become user-visible bugs.

## 1.3 Versioning & branching

Use **Semantic Versioning** `MAJOR.MINOR.PATCH`:

- **MAJOR** — breaking changes (users must adapt).
- **MINOR** — new features, backward-compatible.
- **PATCH** — bug fixes only.

```mermaid
gitGraph
    commit id: "v0.1.0"
    branch feature
    commit id: "work"
    commit id: "work"
    checkout main
    merge feature
    commit id: "v0.2.0" tag: "v0.2.0"
    branch hotfix
    commit id: "fix"
    checkout main
    merge hotfix
    commit id: "v0.2.1" tag: "v0.2.1"
```

`main` stays releasable; develop on branches; tag releases off `main`; keep a human `CHANGELOG.md`.

## 1.4 The build & release pipeline (CI/CD)

Automate so releasing is *boring and repeatable* — a human should never hand-assemble an artifact.

```mermaid
flowchart LR
    T[git tag v*] --> CI[CI runner]
    CI --> S1[Install toolchain<br/>+ pinned deps]
    S1 --> S2[Generate content<br/>/ assets]
    S2 --> S3[Run tests<br/>=GATE=]
    S3 -- fail --> X[Stop, notify]
    S3 -- pass --> S4[Build binary]
    S4 --> S5[Package installer]
    S5 --> S6[Sign + notarize]
    S6 --> S7[Upload to release]
    S7 --> R[(Release artifact)]
```

Trigger on a **tag** (not every commit) so releases are deliberate. The tests step is a hard gate.

## 1.5 Packaging & signing (what makes it feel "real")

```mermaid
flowchart TD
    BIN[Raw executable] --> PKG{Target OS}
    PKG -- Windows --> W[Installer: Inno Setup / WiX → .msi/.exe]
    PKG -- macOS --> M[.app → .dmg]
    PKG -- Linux --> L[AppImage / Flatpak / .deb]
    W --> SW[Code-sign<br/>OV/EV cert]
    M --> SM[Sign + notarize<br/>Apple Developer]
    L --> SL[GPG sign / repo]
    SW --> DIST[Distribute]
    SM --> DIST
    SL --> DIST
```

- **Installer** gives shortcuts, an uninstaller, file associations — not just a loose binary.
- **Signing** removes "Unknown publisher" / Gatekeeper blocks. This is the **first real cost**
  (Windows cert ~$200–400/yr; Apple Developer $99/yr). A $0 product ships unsigned with a documented
  "Run anyway" note — acceptable for personal/portfolio tools, not for wide public distribution.

## 1.6 Distribution channels

| Channel | Cost | Best for |
|---|---|---|
| GitHub Releases | $0 | Versioned downloads, open or personal tools |
| itch.io | $0 | Indie / visual apps; free auto-updating launcher |
| Microsoft Store | ~$19 once | Windows discovery + trust |
| Mac App Store | $99/yr | macOS reach (strict sandbox + review) |
| Steam | $100/app | Games / interactive tools with an audience |
| Self-host + website | hosting cost | Full control, your own brand |

## 1.7 The maintenance loop (after launch)

```mermaid
flowchart LR
    U[Users run app] --> T[Telemetry / crash reports<br/>opt-in, privacy-first]
    U --> FB[Issue tracker /<br/>feature requests]
    T --> TR[Triage + reproduce]
    FB --> TR
    TR --> PRI{Severity?}
    PRI -- critical --> HOT[Hotfix → PATCH release]
    PRI -- normal --> PLAN[Backlog → next MINOR]
    HOT --> REL[Release pipeline]
    PLAN --> DEV[Development]
    DEV --> REL
    REL --> U
```

- **Crash/error reporting** (e.g. Sentry free tier, or local logs the user attaches) tells you it's
  broken *before* users complain.
- **Updates**: manual re-download to start; add auto-update (check a releases API, prompt) only when you
  have real users.
- **Support surface**: README, a docs page, issue templates, and — for a visual app — a demo GIF/video.

## 1.8 The cross-cutting concerns (don't forget)

```mermaid
mindmap
  root((Production<br/>readiness))
    Legal
      LICENSE
      Third-party notices
      Privacy statement
    Security
      Signed artifacts
      Dependency pinning
      No secrets in build
    Quality
      Automated tests = gate
      Clean-machine smoke test
      Reproducible builds
    Users
      Docs + changelog
      Installer + uninstaller
      Update path
    Ops
      Crash reporting
      Versioning
      Issue triage
```

---

# Part 2 — Loupe-specific steps

Loupe has **two halves**, and keeping them separate is the key architectural rule:

```mermaid
flowchart LR
    subgraph BUILDTIME["Build time (Python, your machine / CI)"]
        EQ[render_equations.py<br/>LaTeX → assets/eqn/*.png]
        GEN[gen_models.py<br/>adapter → ir/samples/gen/*.json + catalog.json]
        EQ --> GEN
    end
    subgraph RUNTIME["Runtime (the shipped .exe — pure Godot)"]
        ENG[Godot engine app] --> READS[reads baked-in IR JSON + eqn PNGs]
    end
    GEN -- baked into export --> RUNTIME
```

> **The trap to avoid:** never bundle the Python adapter into the runtime. The adapter is a *build-time*
> content generator; the shipped app is a self-contained Godot binary that only reads pre-generated IR.
> This keeps the desktop app dependency-free, fast, and simple for users.

## 2.1 One-time setup (per machine / CI runner)

```mermaid
flowchart TD
    A[Install Godot 4.7 standard] --> B[Install export templates<br/>matching 4.7]
    B --> C[Author export_presets.cfg<br/>Windows Desktop, embedded PCK, icon]
    C --> D[Ready to build]
```

- **Export templates** (~1 GB, version-pinned): `Godot --headless --install-export-templates`, or via the
  editor's *Manage Export Templates*. Only re-downloaded when you **upgrade Godot** (e.g. 4.7 → 4.8).
- **Export preset**: a `export_presets.cfg` with a `Windows Desktop` preset (embedded `.pck`, `icon.svg`).

## 2.2 The build flow (every release)

```mermaid
flowchart TD
    S0{What changed?}
    S0 -- "Equations" --> E1[python tools/render_equations.py]
    S0 -- "Model / adapter" --> E2[python tools/gen_models.py]
    S0 -- "Engine / GDScript only" --> SK[skip generation]
    E1 --> E2
    E2 --> T1[cd ingest; pytest =GATE=]
    SK --> IMP
    T1 --> IMP[Godot --headless --import]
    IMP --> V[Godot --headless --script tools/verify.gd<br/>expect RESULT PASS =GATE=]
    V -- fail --> STOP[Fix, retry]
    V -- pass --> X[Godot --headless --export-release<br/>Windows Desktop preset → build/loupe.exe]
    X --> SMOKE[Launch loupe.exe,<br/>load a model =GATE=]
```

Because the `.exe` reads **baked-in** JSON/PNGs, any new model or equation must be regenerated **before**
export — otherwise it won't appear in the build.

### One-command build (recommended)

A `tools/build.ps1` that chains the flow so a release is a single command:

```powershell
# tools/build.ps1  (illustrative)
python tools/render_equations.py
python tools/gen_models.py
Push-Location ingest; python -m pytest -q; if ($LASTEXITCODE) { throw "tests failed" }; Pop-Location
$GODOT = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\GodotEngine.GodotEngine_*\Godot_v4.7-stable_win64.exe").FullName
& $GODOT --headless --path . --import
& $GODOT --headless --path . --script res://tools/verify.gd   # exits non-zero on FAIL
if ($LASTEXITCODE) { throw "verify failed" }
New-Item -ItemType Directory -Force build | Out-Null
& $GODOT --headless --path . --export-release "Windows Desktop" build/loupe.exe
```

Then any update = edit → `./tools/build.ps1` → ship `build/loupe.exe`.

## 2.3 Update decision tree (which gates apply)

```mermaid
flowchart TD
    C{Change type}
    C -- "New model template" --> R1[render_equations? if new eqns]
    R1 --> R2[gen_models.py]
    R2 --> R3[pytest + verify + export]
    C -- "Lens / shell / shader" --> R4[verify.gd + export]
    C -- "Hand-authored sample" --> R5[verify.gd + export]
    C -- "Docs only" --> R6[no rebuild needed]
    C -- "Godot version upgrade" --> R7[re-install export templates first]
    R7 --> R4
```

## 2.4 Publishing Loupe (recommended $0 path, in order)

```mermaid
flowchart LR
    A[Tag v0.x.0] --> B[build.ps1 → loupe.exe]
    B --> C[GitHub Release<br/>attach loupe.exe + notes]
    C --> D[Users download + run]
    D -.->|later| E[GitHub Actions:<br/>auto-build on tag]
    D -.->|later| F[Inno Setup installer]
    D -.->|later| G[itch.io + Butler auto-update]
    D -.->|with users| H[Code signing + crash logs]
```

1. **Now:** `README.md`, `build.ps1`, export preset, **GitHub Releases** with an unsigned `loupe.exe` and a
   "More info → Run anyway" note. ($0, shippable today.)
2. **Soon:** GitHub Actions to run `build.ps1` on every `v*` tag and attach the artifact; an Inno Setup
   installer; a demo GIF; a docs page (GitHub Pages).
3. **When you have users:** Windows code signing (EV first), auto-update against the Releases API, opt-in
   local crash logs.
4. **If you want reach:** itch.io, then the Microsoft Store.

## 2.5 Loupe release checklist

- [ ] `decisions.md` updated for any architectural change (ADR LP-NNN).
- [ ] `handoff.md` reflects current state.
- [ ] `python tools/render_equations.py` (if equations changed).
- [ ] `python tools/gen_models.py` (if any model/template changed) → `catalog.json` regenerated.
- [ ] `cd ingest && python -m pytest -q` → all pass.
- [ ] `Godot --headless --script res://tools/verify.gd` → **RESULT PASS**.
- [ ] Version bumped in `project.godot`; `CHANGELOG.md` entry added; git tag `vX.Y.Z`.
- [ ] `build.ps1` produces `build/loupe.exe`; launched on a clean window and a model loads.
- [ ] GitHub Release created; `loupe.exe` attached; "how to run unsigned" note included.

---

*Generic lifecycle is reusable for any product; Part 2 is the concrete mapping for Loupe. Keep build-time
generation and runtime strictly separated — that single rule keeps the shipped app simple.*
