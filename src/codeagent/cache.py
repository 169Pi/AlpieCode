"""
Response cache for AlpieCode.

Caches LLM responses on disk (~/.alpiecode/cache/) so identical prompts
return instantly without model inference. Shared across CLI, IDE, and VS Code.

Design:
  - Cache key = SHA-256 hash of normalized task text
  - Only caches "pure" responses (no tool calls — those are context-dependent)
  - In-memory LRU + disk persistence for instant lookups across restarts
  - TTL: 7 days, Max entries: 500
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

CACHE_DIR = Path.home() / ".alpiecode" / "cache"
MAX_ENTRIES = 500
TTL_SECONDS = 7 * 24 * 3600  # 7 days


class ResponseCache:
    """Disk-backed LRU response cache."""

    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        max_entries: int = MAX_ENTRIES,
        ttl: int = TTL_SECONDS,
    ):
        self.cache_dir = cache_dir
        self.max_entries = max_entries
        self.ttl = ttl
        self._mem: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        self._warm_up()

    # ── Public API ──────────────────────────────────────────────────────

    def get(self, task: str) -> Optional[Dict[str, Any]]:
        """
        Look up a cached response for the given task.

        Returns dict with keys: response, reasoning (optional), cached_at
        Returns None on cache miss or expired entry.
        """
        key = self._key(task)

        # Memory check (fast path)
        entry = self._mem.get(key)
        if entry and self._is_valid(entry):
            self._hits += 1
            return entry

        # Disk check (slow path)
        path = self._path(key)
        if path.exists():
            try:
                entry = json.loads(path.read_text(encoding="utf-8"))
                if self._is_valid(entry):
                    self._mem[key] = entry  # Promote to memory
                    self._hits += 1
                    return entry
                else:
                    path.unlink(missing_ok=True)  # Expired
            except Exception:
                pass

        self._misses += 1
        return None

    def put(self, task: str, response: str, reasoning: Optional[str] = None) -> None:
        """
        Store a response in the cache.

        Only call this for responses that completed WITHOUT tool calls.
        """
        if not response or not task.strip():
            return

        key = self._key(task)
        entry = {
            "task": task.strip(),
            "response": response,
            "reasoning": reasoning,
            "cached_at": time.time(),
        }

        self._mem[key] = entry

        # Write to disk
        try:
            path = self._path(key)
            path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

        self._enforce_limit()

    def clear(self) -> int:
        """Clear all cached responses. Returns number of entries removed."""
        count = 0
        try:
            for f in self.cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
                count += 1
        except OSError:
            pass
        self._mem.clear()
        return count

    @property
    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        disk_count = len(list(self.cache_dir.glob("*.json"))) if self.cache_dir.exists() else 0
        total = self._hits + self._misses
        return {
            "entries": disk_count,
            "memory": len(self._mem),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "0%",
        }

    # ── Internals ───────────────────────────────────────────────────────

    def _key(self, task: str) -> str:
        """Normalize and hash the task text into a 16-char hex key."""
        normalized = " ".join(task.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _is_valid(self, entry: Dict[str, Any]) -> bool:
        cached_at = entry.get("cached_at", 0)
        return (time.time() - cached_at) < self.ttl

    def _warm_up(self):
        """Load the 100 most recent entries into memory on startup."""
        if not self.cache_dir.exists():
            return
        try:
            files = sorted(
                self.cache_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            for f in files[:100]:
                try:
                    entry = json.loads(f.read_text(encoding="utf-8"))
                    if self._is_valid(entry):
                        self._mem[f.stem] = entry
                    else:
                        f.unlink(missing_ok=True)  # Clean expired
                except Exception:
                    pass
        except OSError:
            pass

    def _enforce_limit(self):
        """Evict oldest entries if over max_entries."""
        if not self.cache_dir.exists():
            return
        try:
            files = sorted(self.cache_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
            while len(files) > self.max_entries:
                oldest = files.pop(0)
                key = oldest.stem
                oldest.unlink(missing_ok=True)
                self._mem.pop(key, None)
        except OSError:
            pass


# ── Singleton ───────────────────────────────────────────────────────────
_CACHE: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get or create the global response cache singleton."""
    global _CACHE
    if _CACHE is None:
        _CACHE = ResponseCache()
    return _CACHE
