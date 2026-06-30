"""GitHub repository → IR (deterministic, **0 tokens**, real web data).

Source forms: ``github:owner/repo`` or a github.com URL, or ``kind_hint='github'``. Fetches the recursive
git tree via the public GitHub API and builds the directory/file CONTAINMENT hierarchy — the repo's real
structure, which renders with the existing structure/text lens (dirs explode to reveal files).

LOD bands track directory depth so zooming in reveals deeper folders. A token in ``GITHUB_TOKEN`` raises
the rate limit but is not required for public repos.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Optional

from ..ir import Document, Entity, LODPolicy, Payload, Relation
from .base import IngestContext, Ingestor, Source

_REPO = "https://api.github.com/repos/{owner}/{repo}"
_TREE = "https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
_MAX_NODES = 400  # keep the scene legible; deep/large repos are summarized


def _accent(rgb):
    return [round(c, 3) for c in rgb]


class GitHubIngestor(Ingestor):
    uses_llm = False

    @property
    def name(self) -> str:
        return "github"

    @staticmethod
    def _extract_repo(raw: Any) -> Optional[tuple[str, str]]:
        if not isinstance(raw, str):
            return None
        s = raw.strip()
        if s.lower().startswith("github:"):
            s = s.split(":", 1)[1]
        if "github.com/" in s:
            s = s.split("github.com/", 1)[1]
        s = s.strip("/").removesuffix(".git")
        parts = s.split("/")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return parts[0], parts[1]
        return None

    def can_handle(self, source: Source) -> bool:
        if source.kind_hint == "github":
            return self._extract_repo(source.raw) is not None
        raw = source.raw
        if isinstance(raw, str) and (raw.lower().startswith("github:") or "github.com/" in raw):
            return self._extract_repo(raw) is not None
        return False

    def ingest(self, source: Source, ctx: IngestContext) -> Document:
        repo = self._extract_repo(source.raw)
        if not repo:
            raise ValueError(f"Could not parse owner/repo from {source.raw!r}")
        owner, name = repo

        info = ctx.cache.memoize(ctx.cache.key("gh-repo", owner, name),
                                 lambda: self._fetch_json(_REPO.format(owner=owner, repo=name))) \
            if ctx.cache else self._fetch_json(_REPO.format(owner=owner, repo=name))
        branch = info.get("default_branch", "main")
        desc = info.get("description") or ""

        tree = ctx.cache.memoize(ctx.cache.key("gh-tree", owner, name, branch),
                                 lambda: self._fetch_json(_TREE.format(owner=owner, repo=name, branch=branch))) \
            if ctx.cache else self._fetch_json(_TREE.format(owner=owner, repo=name, branch=branch))

        ents: list[Entity] = []
        root_id = "repo"
        ents.append(Entity(
            id=root_id, label=f"{owner}/{name}", kind="repository", parent=None, lod_band=0,
            payload=Payload.make("text", {"accent": _accent((0.5, 0.85, 1.0)), "width": 2.6, "height": 1.3}),
            content_tiers={"overview": f"{owner}/{name}", "detail": desc[:200],
                           "deep": f"branch {branch} · {len(tree.get('tree', []))} entries"},
        ))

        seen: set[str] = {""}  # paths whose entity exists ("" = root)
        items = sorted(tree.get("tree", []), key=lambda t: t.get("path", ""))
        count = 0
        for item in items:
            if count >= _MAX_NODES:
                break
            path = item.get("path", "")
            if not path:
                continue
            is_dir = item.get("type") == "tree"
            parent_path = path.rsplit("/", 1)[0] if "/" in path else ""
            # Ensure ancestor dirs exist (the API tree already lists them, but be safe on ordering).
            if parent_path not in seen:
                continue
            depth = path.count("/")
            ents.append(Entity(
                id=self._safe_id(path),
                label=path.rsplit("/", 1)[-1],
                kind="dir" if is_dir else "file",
                parent=root_id if parent_path == "" else self._safe_id(parent_path),
                lod_band=min(depth, 2),
                payload=Payload.make("text", {
                    "accent": _accent((0.45, 0.8, 1.0) if is_dir else (0.6, 0.95, 0.85)),
                    "width": 1.1, "height": 0.6,
                }),
                content_tiers={"overview": path.rsplit("/", 1)[-1]},
            ))
            seen.add(path)
            count += 1

        doc = Document(root=root_id, entities=ents, relations=[],
                       lod_policy=LODPolicy(bands=3, distance_thresholds=[6.0, 3.2]))
        doc.provenance = None
        return doc

    @staticmethod
    def _safe_id(path: str) -> str:
        return "f_" + path.replace("/", "__").replace(".", "_").replace("-", "_")

    @staticmethod
    def _fetch_json(url: str) -> dict:
        headers = {"User-Agent": "loupe-ingest/0.1", "Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8"))
