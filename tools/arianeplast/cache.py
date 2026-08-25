"""On-disk HTTP cache for arianeplast.com.

Every network access made by the Arianeplast tooling goes through ``fetch()``.
The point is that the manufacturer's server is hit *once* per URL: subsequent
runs (and subsequent analysis passes) read the stored HTML from disk.

Layout of the cache directory (``.cache/arianeplast`` by default):

    pages/<sha1-of-url>.html    raw response body
    pages/<sha1-of-url>.json    metadata: url, fetched_at, status, content-type
    index.json                  url -> entry filename, for lookups and search

Politeness rules enforced here:
  * one request at a time, with a minimum delay between two requests
    (``--delay``, default 2s);
  * a cached page is never re-fetched unless it is older than the TTL
    (default: 30 days) or ``force=True`` is passed;
  * a descriptive User-Agent identifying the project;
  * only hosts in ``ALLOWED_HOSTS`` may be fetched.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

ALLOWED_HOSTS = {"www.arianeplast.com", "arianeplast.com"}

USER_AGENT = (
    "OpenPrintTagDatabaseBot/1.0 "
    "(+https://github.com/OpenPrintTag/openprinttag-database; "
    "cached crawler, one request per page)"
)

DEFAULT_CACHE_DIR = Path(".cache/arianeplast")
DEFAULT_TTL_DAYS = 30
DEFAULT_DELAY = 2.0


class BlockedHostError(RuntimeError):
    """Raised when a URL points outside the manufacturer's site."""


@dataclass
class CacheEntry:
    url: str
    path: Path
    fetched_at: datetime
    status: int
    from_cache: bool

    def text(self) -> str:
        return self.path.read_text(encoding="utf-8", errors="replace")


def _key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _check_host(url: str) -> None:
    host = urllib.parse.urlsplit(url).hostname or ""
    if host.lower() not in ALLOWED_HOSTS:
        raise BlockedHostError(
            f"refusing to fetch {url!r}: host {host!r} is outside {sorted(ALLOWED_HOSTS)}"
        )


class Cache:
    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        ttl_days: int = DEFAULT_TTL_DAYS,
        delay: float = DEFAULT_DELAY,
    ) -> None:
        self.dir = Path(cache_dir)
        self.pages = self.dir / "pages"
        self.pages.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.json"
        self.ttl = timedelta(days=ttl_days)
        self.delay = delay
        self._last_request = 0.0
        self.index: dict[str, dict] = {}
        if self.index_path.exists():
            self.index = json.loads(self.index_path.read_text(encoding="utf-8"))

    # -- persistence ------------------------------------------------------

    def save_index(self) -> None:
        self.index_path.write_text(
            json.dumps(self.index, indent=1, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

    # -- reading ----------------------------------------------------------

    def get(self, url: str) -> Optional[CacheEntry]:
        """Return the cached entry for ``url``, fresh or stale, or None."""
        meta = self.index.get(url)
        if not meta:
            return None
        path = self.pages / meta["file"]
        if not path.exists():
            return None
        return CacheEntry(
            url=url,
            path=path,
            fetched_at=datetime.fromisoformat(meta["fetched_at"]),
            status=meta["status"],
            from_cache=True,
        )

    def is_fresh(self, url: str) -> bool:
        entry = self.get(url)
        if entry is None:
            return False
        return datetime.now(timezone.utc) - entry.fetched_at < self.ttl

    def entries(self) -> Iterator[CacheEntry]:
        """Iterate over every cached page, for offline searching."""
        for url in sorted(self.index):
            entry = self.get(url)
            if entry is not None:
                yield entry

    # -- fetching ---------------------------------------------------------

    def fetch(self, url: str, force: bool = False) -> CacheEntry:
        """Return ``url``'s content, hitting the network only when needed."""
        _check_host(url)
        if not force and self.is_fresh(url):
            entry = self.get(url)
            assert entry is not None
            return entry

        elapsed = time.monotonic() - self._last_request
        if self._last_request and elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "gzip",
                "Accept-Language": "en",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                status = response.status
                content_type = response.headers.get("Content-Type", "")
        finally:
            self._last_request = time.monotonic()

        key = _key(url)
        path = self.pages / f"{key}.html"
        path.write_bytes(raw)
        fetched_at = datetime.now(timezone.utc)
        meta = {
            "url": url,
            "file": path.name,
            "fetched_at": fetched_at.isoformat(),
            "status": status,
            "content_type": content_type,
            "bytes": len(raw),
        }
        (self.pages / f"{key}.json").write_text(
            json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        self.index[url] = meta
        self.save_index()
        return CacheEntry(
            url=url, path=path, fetched_at=fetched_at, status=status, from_cache=False
        )
