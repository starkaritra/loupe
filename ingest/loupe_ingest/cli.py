"""Command-line entry: ``loupe-ingest <source> -o out.ir.json [--provider gpt|sonnet|gemini|ollama]``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .cache import Cache
from .llm import make_client
from .pipeline import ingest


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="loupe-ingest",
        description="Compile anything (config.json, blueprint, or a concept) into loupe-ir/v1 JSON.",
    )
    p.add_argument("source", help="path to a structured file, or a free-text target in quotes")
    p.add_argument("-o", "--out", default="-", help="output IR path (default: stdout)")
    p.add_argument("--kind", default="", help="explicit domain hint: transformer|blueprint|...")
    p.add_argument("--domain-hint", default="", help="free-text hint passed to the LLM frontier")
    p.add_argument("--provider", default="", help="LLM provider for the frontier: gpt|sonnet|gemini|ollama")
    p.add_argument("--model", default="", help="override the provider's default model")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--no-ground", action="store_true", help="disable web grounding for concept queries")
    p.add_argument("--no-cache", action="store_true", help="disable the content cache")
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--version", action="version", version=f"loupe-ingest {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    llm = None
    if args.provider:
        llm = make_client(args.provider, args.model or None, temperature=args.temperature)

    cache = Cache(enabled=not args.no_cache)
    try:
        doc = ingest(
            args.source,
            kind_hint=args.kind,
            llm=llm,
            cache=cache,
            ground=not args.no_ground,
            domain_hint=args.domain_hint,
            options={"max_tokens": args.max_tokens},
        )
    except Exception as exc:  # noqa: BLE001 - surface a clean CLI error
        print(f"loupe-ingest: error: {exc}", file=sys.stderr)
        return 1

    out_json = doc.to_json()
    if args.out == "-":
        print(out_json)
    else:
        Path(args.out).write_text(out_json, encoding="utf-8")
        prov = doc.provenance
        print(
            f"wrote {args.out}  ({len(doc.entities)} entities, root={doc.root}, "
            f"sha={prov.hash[:12] if prov else '?'}…)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
