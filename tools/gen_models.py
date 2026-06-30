"""Generate engine sample IRs for every model template via the adapter (single source of truth).

Run from the repo root:  ``python tools/gen_models.py``
Writes ``ir/samples/gen/<name>.loupe.json`` for each canonical template plus ``catalog.json`` (the list
the engine cycles through). Adding a template in ``model_arch.py`` automatically yields a new sample here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ingest"))

from loupe_ingest.ingestors.base import IngestContext, Source           # noqa: E402
from loupe_ingest.ingestors.model_arch import ModelArchIngestor          # noqa: E402

# Canonical name per family (the deduped set worth showing in the catalog).
CANON = ["gpt2", "bert", "seq2seq", "vit", "alexnet", "resnet", "unet",
         "lstm", "gru", "mamba", "stable_diffusion", "vae", "gan", "moe"]

OUT = ROOT / "ir" / "samples" / "gen"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ing = ModelArchIngestor()
    ctx = IngestContext(options={"offline": True})       # deterministic; no network during generation
    catalog = []
    for name in CANON:
        doc = ing.ingest(Source(f"modelarch:{name}"), ctx).stamp(
            source=f"modelarch:{name}", generator="model_architecture adapter")
        doc.validate()
        (OUT / f"{name}.loupe.json").write_text(doc.to_json(), encoding="utf-8")
        label = next((e.label for e in doc.entities if e.id == "model"), name)
        catalog.append({"name": name, "label": label, "path": f"res://ir/samples/gen/{name}.loupe.json"})
        print(f"  {name:18s} {len(doc.entities):2d} entities  -> gen/{name}.loupe.json")
    (OUT / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"catalog: {len(catalog)} models -> {OUT/'catalog.json'}")


if __name__ == "__main__":
    main()
