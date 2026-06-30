"""arXiv paper → IR (deterministic, **0 tokens**, real web data).

Source forms: ``arxiv:2407.12844`` / ``arxiv:1706.03762`` or any arxiv.org URL, or ``kind_hint='arxiv'``.
Uses the public arXiv Atom API (no key) for authoritative metadata; best-effort scrapes section headings
from the arXiv HTML rendering when available, else falls back to a metadata hierarchy. Every entity is
``text`` so it renders with the existing structure/text lens.

    paper → [Abstract, Authors, Categories, (Section 1..N if HTML available)]
"""
from __future__ import annotations

import re
import urllib.request
from typing import Any, Optional
from xml.etree import ElementTree as ET

from ..ir import Document, Entity, LODPolicy, Payload, Relation
from .base import IngestContext, Ingestor, Source

_API = "http://export.arxiv.org/api/query?id_list={}"
_HTML = "https://arxiv.org/html/{}"
_ATOM = "{http://www.w3.org/2005/Atom}"
_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(v\d+)?)")


def _accent(rgb):
    return [round(c, 3) for c in rgb]


class ArxivIngestor(Ingestor):
    uses_llm = False

    @property
    def name(self) -> str:
        return "arxiv"

    @staticmethod
    def _extract_id(raw: Any) -> Optional[str]:
        if not isinstance(raw, str):
            return None
        s = raw.strip()
        if s.lower().startswith("arxiv:"):
            s = s.split(":", 1)[1]
        m = _ID_RE.search(s)
        return m.group(1) if m else None

    def can_handle(self, source: Source) -> bool:
        if source.kind_hint == "arxiv":
            return self._extract_id(source.raw) is not None
        raw = source.raw
        if isinstance(raw, str) and ("arxiv.org" in raw or raw.lower().startswith("arxiv:")):
            return self._extract_id(raw) is not None
        return False

    def ingest(self, source: Source, ctx: IngestContext) -> Document:
        arxiv_id = self._extract_id(source.raw)
        if not arxiv_id:
            raise ValueError(f"Could not parse an arXiv id from {source.raw!r}")

        meta = ctx.cache.memoize(ctx.cache.key("arxiv-api", arxiv_id), lambda: self._fetch_meta(arxiv_id)) \
            if ctx.cache else self._fetch_meta(arxiv_id)

        ents: list[Entity] = []
        rels: list[Relation] = []
        root_id = "paper"
        ents.append(Entity(
            id=root_id, label=meta["title"], kind="paper", parent=None, lod_band=0,
            payload=Payload.make("text", {"accent": _accent((0.45, 0.95, 0.8)), "width": 2.8, "height": 1.5}),
            content_tiers={
                "overview": meta["title"],
                "detail": f"{', '.join(meta['authors'][:4])}{' et al.' if len(meta['authors']) > 4 else ''}",
                "deep": meta["summary"][:600],
            },
        ))
        ents.append(Entity(
            id="abstract", label="Abstract", kind="section", parent=root_id, lod_band=0,
            payload=Payload.make("text", {"accent": _accent((0.5, 0.9, 0.85))}),
            content_tiers={"overview": meta["summary"][:240], "detail": meta["summary"][:800]},
        ))
        ents.append(Entity(
            id="authors", label="Authors", kind="section", parent=root_id, lod_band=1,
            payload=Payload.make("text", {"accent": _accent((0.5, 0.85, 1.0))}),
            content_tiers={"overview": ", ".join(meta["authors"])},
        ))
        ents.append(Entity(
            id="categories", label="Categories", kind="section", parent=root_id, lod_band=1,
            payload=Payload.make("text", {"accent": _accent((0.6, 0.8, 1.0))}),
            content_tiers={"overview": ", ".join(meta["categories"])},
        ))
        rels.append(Relation("abstract", "authors", "relates_to"))

        # Best-effort: real section headings from the HTML rendering.
        sections = ctx.cache.memoize(ctx.cache.key("arxiv-html", arxiv_id),
                                     lambda: self._fetch_sections(arxiv_id)) if ctx.cache \
            else self._fetch_sections(arxiv_id)
        prev = "abstract"
        for i, title in enumerate(sections[:12]):
            sid = f"sec_{i}"
            ents.append(Entity(
                id=sid, label=title, kind="section", parent=root_id, lod_band=0,
                payload=Payload.make("text", {"accent": _accent((0.45, 0.85, 1.0)), "width": 1.5, "height": 0.9}),
                content_tiers={"overview": title},
            ))
            rels.append(Relation(prev, sid, "flow"))
            prev = sid

        doc = Document(root=root_id, entities=ents, relations=rels,
                       lod_policy=LODPolicy(bands=3, distance_thresholds=[5.5, 3.0]))
        doc.provenance = None
        return doc

    @staticmethod
    def _fetch_meta(arxiv_id: str) -> dict:
        req = urllib.request.Request(_API.format(arxiv_id), headers={"User-Agent": "loupe-ingest/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            xml = r.read().decode("utf-8")
        root = ET.fromstring(xml)
        entry = root.find(f"{_ATOM}entry")
        if entry is None:
            raise ValueError(f"arXiv returned no entry for {arxiv_id}")
        title = (entry.findtext(f"{_ATOM}title") or "").strip().replace("\n", " ")
        summary = (entry.findtext(f"{_ATOM}summary") or "").strip().replace("\n", " ")
        authors = [a.findtext(f"{_ATOM}name") or "" for a in entry.findall(f"{_ATOM}author")]
        cats = [c.get("term", "") for c in entry.findall("{http://arxiv.org/schemas/atom}primary_category")]
        cats += [c.get("term", "") for c in entry.findall(f"{_ATOM}category")]
        return {"title": title, "summary": summary, "authors": authors,
                "categories": sorted(set(c for c in cats if c))}

    @staticmethod
    def _fetch_sections(arxiv_id: str) -> list[str]:
        try:
            req = urllib.request.Request(_HTML.format(arxiv_id), headers={"User-Agent": "loupe-ingest/0.1"})
            with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
                html = r.read().decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001 - HTML rendering may not exist; metadata hierarchy is enough
            return []
        # arXiv HTML marks sections with <h2 class="ltx_title ltx_title_section">.
        titles = re.findall(r'<h2[^>]*ltx_title_section[^>]*>(.*?)</h2>', html, re.S)
        out: list[str] = []
        for t in titles:
            clean = re.sub(r"<[^>]+>", "", t)
            clean = re.sub(r"\s+", " ", clean).strip()
            if clean:
                out.append(clean[:60])
        return out
