"""On-disk cache for weather responses, keyed by the full request URL.

Each entry is one JSON file named by the SHA-256 of the URL, holding the URL,
the fetch time and the response body. Entries older than the time-to-live are
ignored; a time-to-live of None never expires (used for the historical
archive, whose data do not change once published).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path


def default_cache_dir() -> Path:
    """Return ``$XDG_CACHE_HOME/blagden/open-meteo``, or ``~/.cache/blagden/open-meteo``."""
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "blagden" / "open-meteo"


class DiskCache:
    """A small file cache. ``clock`` returns seconds since the epoch and exists for tests."""

    def __init__(self, directory: Path | None = None, clock: Callable[[], float] = time.time):
        self.directory = directory if directory is not None else default_cache_dir()
        self.clock = clock

    def path_for(self, url: str) -> Path:
        """Return the file that holds the entry for ``url``."""
        return self.directory / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"

    def get(self, url: str, ttl_s: float | None) -> bytes | None:
        """Return the cached body for ``url`` if present and fresh, else None."""
        path = self.path_for(url)
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if entry.get("url") != url:
            return None
        if ttl_s is not None and self.clock() - float(entry["fetched_s"]) > ttl_s:
            return None
        body = entry.get("body")
        return body.encode("utf-8") if isinstance(body, str) else None

    def put(self, url: str, body: bytes) -> None:
        """Store ``body`` for ``url``, replacing any older entry atomically."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(url)
        tmp = path.with_suffix(".tmp")
        entry = {"url": url, "fetched_s": self.clock(), "body": body.decode("utf-8")}
        tmp.write_text(json.dumps(entry), encoding="utf-8")
        tmp.replace(path)
