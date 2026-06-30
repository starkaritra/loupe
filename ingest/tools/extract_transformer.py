"""Extract loupe-ingest inputs from a LIVE transformer — the concrete "extract the i/ps" path.

Two modes, both $0 and offline-friendly:

  # 1. From a Hugging Face model id or local dir (just its config — no weights, no torch needed):
  python tools/extract_transformer.py --hf gpt2 -o gpt2_config.json

  # 2. From a live torch.nn.Module you already have (introspect the real module tree):
  #    (requires torch; reads structure only, never weights)
  python tools/extract_transformer.py --module my_pkg.build:make_model -o model_config.json

The output is a plain config dict the deterministic TransformerIngestor compiles with 0 tokens:
  loupe-ingest model_config.json --kind transformer -o model.ir.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def from_hf_config(name_or_path: str) -> dict:
    """Read a HF config.json from a local dir or the hub (config only; no weights/torch)."""
    p = Path(name_or_path)
    local = p / "config.json" if p.is_dir() else p
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))
    try:
        from transformers import AutoConfig  # lazy/optional
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "transformers not installed and no local config.json found. "
            "pip install transformers, or pass a path to a config.json."
        ) from exc
    cfg = AutoConfig.from_pretrained(name_or_path)
    return cfg.to_dict()


def from_live_module(spec: str) -> dict:
    """Introspect a live torch module. ``spec`` = 'package.module:factory' returning an nn.Module.

    Derives n_layers/n_heads/d_model by walking ``named_modules()`` — structure only, never weights.
    """
    try:
        import importlib

        import torch  # noqa: F401  (ensures torch present)
        import torch.nn as nn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("torch required for --module introspection. pip install torch") from exc

    mod_path, _, factory = spec.partition(":")
    module = importlib.import_module(mod_path)
    model = getattr(module, factory)() if factory else module

    n_layers = 0
    n_heads = 0
    d_model = 0
    for _, m in model.named_modules():
        cls = m.__class__.__name__.lower()
        if "decoderlayer" in cls or "encoderlayer" in cls or cls.endswith("block"):
            n_layers += 1
        if isinstance(m, nn.MultiheadAttention):
            n_heads = max(n_heads, getattr(m, "num_heads", 0))
            d_model = max(d_model, getattr(m, "embed_dim", 0))
        for attr in ("num_heads", "n_head", "num_attention_heads"):
            if hasattr(m, attr):
                n_heads = max(n_heads, int(getattr(m, attr)))
    return {
        "model_type": model.__class__.__name__,
        "_name_or_path": model.__class__.__name__,
        "num_hidden_layers": n_layers or 1,
        "num_attention_heads": n_heads or 1,
        "hidden_size": d_model or 0,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Extract a transformer config for loupe-ingest.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--hf", help="HF model id or local dir (reads config.json only)")
    g.add_argument("--module", help="'package.module:factory' returning a live torch.nn.Module")
    ap.add_argument("-o", "--out", default="-", help="output config path (default: stdout)")
    args = ap.parse_args(argv)

    cfg = from_hf_config(args.hf) if args.hf else from_live_module(args.module)
    blob = json.dumps(cfg, indent=2)
    if args.out == "-":
        print(blob)
    else:
        Path(args.out).write_text(blob, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
