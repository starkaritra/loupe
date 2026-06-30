"""Content-addressed cache — the backbone of token-frugality and reproducibility (LP-013).

Every expensive/non-deterministic step (LLM calls, web fetches) is keyed by a hash of its inputs and
stored on disk. Re-running the same ingestion costs **0 tokens** and yields identical output. Pure
stdlib so the package stays dependency-free on the common path.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Optional


def _default_dir() -> Path:
    env = os.environ.get("LOUPE_CACHE_DIR")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "loupe-ingest"


class Cache:
    def __init__(self, directory: Optional[os.PathLike[str] | str] = None, enabled: bool = True) -> None:
        self.dir = Path(directory) if directory is not None else _default_dir()
        self.enabled = enabled

    @staticmethod
    def key(*parts: Any) -> str:
        blob = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        p = self._path(key)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))["value"]
            except (json.JSONDecodeError, KeyError, OSError):
                return None
        return None

    def put(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(json.dumps({"value": value}), encoding="utf-8")

    def memoize(self, key: str, produce: Callable[[], Any]) -> Any:
        """Return cached value for ``key`` or compute, store, and return it."""
        hit = self.get(key)
        if hit is not None:
            return hit
        value = produce()
        self.put(key, value)
        return value
