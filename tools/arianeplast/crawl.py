"""Scope-limited crawler for arianeplast.com product pages.

The crawl is deliberately narrow: it walks the category listings named on the
command line (PLA only, by default), follows their pagination, and fetches the
product pages found there. Nothing else on the site is touched — no blog, no
cart, no account pages, no images.

Everything goes through ``cache.Cache``, so a second run costs zero requests
unless the cache has expired or ``--force`` is passed.

    # what would be fetched, without touching the network
    python tools/arianeplast/crawl.py --dry-run

    # PLA categories, the default scope
    python tools/arianeplast/crawl.py

    # a different scope
    python tools/arianeplast/crawl.py --category pla-format-1-kg --category petg
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cache import DEFAULT_CACHE_DIR, DEFAULT_DELAY, DEFAULT_TTL_DAYS, Cache  # noqa: E402

BASE = "https://www.arianeplast.com"
LANG = "en"

# Category slugs that make up the PLA scope, as they appear in product URLs
# already recorded in data/materials/arianeplast/.
PLA_CATEGORIES = [
    "pla-format-1-kg",
    "pla-format-8kg",
    "pla-format-23kg",
    "filaments-carbone",
]

# https://www.arianeplast.com/en/<category-slug>/<id>-<product-slug>.html
PRODUCT_RE = re.compile(
    r'href="(https://www\.arianeplast\.com/[a-z]{2}/[a-z0-9-]+/\d+[^"]*\.html)"'
)


def category_url(slug: str, page: int = 1) -> str:
    url = f"{BASE}/{LANG}/{slug}"
    return f"{url}?page={page}" if page > 1 else url


def clean_product_url(url: str) -> str:
    """Drop the ``#/1-diametre-175mm`` style fragments and query strings."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def product_links(html: str, category: str) -> list[str]:
    found = []
    for raw in PRODUCT_RE.findall(html):
        url = clean_product_url(raw)
        if f"/{category}/" in url and url not in found:
            found.append(url)
    return found


def has_next_page(html: str, page: int) -> bool:
    return f"page={page + 1}" in html


def crawl(
    cache: Cache, categories: list[str], max_pages: int, force: bool, dry_run: bool
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for category in categories:
        products: list[str] = []
        for page in range(1, max_pages + 1):
            url = category_url(category, page)
            if dry_run:
                print(f"[dry-run] listing {url}")
                break
            entry = cache.fetch(url, force=force)
            origin = "cache" if entry.from_cache else "network"
            html = entry.text()
            links = product_links(html, category)
            print(f"  {category} p{page} ({origin}): {len(links)} products")
            for link in links:
                if link not in products:
                    products.append(link)
            if not has_next_page(html, page):
                break
        result[category] = products

    total = sum(len(v) for v in result.values())
    print(f"\n{total} product pages in scope")
    if dry_run:
        return result

    for category, urls in result.items():
        for url in urls:
            entry = cache.fetch(url, force=force)
            origin = "cache" if entry.from_cache else "network"
            print(f"  [{origin}] {url}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        help="category slug to crawl (repeatable); defaults to the PLA scope",
    )
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument(
        "--force", action="store_true", help="re-fetch even when cached and fresh"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the scope without any request"
    )
    args = parser.parse_args()

    cache = Cache(args.cache_dir, ttl_days=args.ttl_days, delay=args.delay)
    categories = args.categories or PLA_CATEGORIES
    print(f"scope: {', '.join(categories)}")
    crawl(cache, categories, args.max_pages, args.force, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
