"""Scope-limited crawler for arianeplast.com product pages.

The list of product pages comes from the shop's own English sitemap rather than
from walking the category listings: it is exhaustive, it costs a single request
instead of one per listing page, and it gives the canonical ``/en/`` URL of every
product — the form this database wants to store.

The crawl stays narrow: only the categories named on the command line (the PLA
scope, by default) are fetched. Nothing else on the site is touched — no blog,
no cart, no account pages, no images.

Everything goes through ``cache.Cache``, so a second run costs zero requests
unless the cache has expired or ``--force`` is passed.

    # what would be fetched, without fetching a single product page
    python tools/arianeplast/crawl.py --dry-run

    # PLA categories, the default scope
    python tools/arianeplast/crawl.py

    # a different scope
    python tools/arianeplast/crawl.py --category 3d-filament-petg
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

# The sitemap is served by the apex host, which redirects dynamic routes to www
# but serves static files fine.
SITEMAP_URL = "https://arianeplast.com/1_en_0_sitemap.xml"

# Categories that may hold a PLA product. Membership is *not* decided here: the
# category only narrows what gets fetched, and `extract.py` then reads the
# "Material" row of each product's data sheet to tell PLA from the rest.
PLA_CATEGORIES = [
    # spool formats
    "pla-format-1-kg",
    "pla-format-23kg",
    "pla-format-8kg",
    "pla-format-10m",
    "pla-format-315g",
    # spool-less refills
    "refill-pla",
    # ranges that are PLA or PLA-based, to be confirmed per product
    "pla-eco-arianeplast",
    "3d-filaments-pla",
    "3d-filaments-wood",
    "3d-filament-recycle",
    "3d-filaments-marquage-laser-",
    "filaments-carbone",
    "filaments-litophanie",
    "haute-resistance",
    "basic-series",
    "conducteur-electrique",
]

LOC_RE = re.compile(r"<loc><!\[CDATA\[([^\]]+)\]\]></loc>")


def clean_product_url(url: str) -> str:
    """Drop the ``#/1-diametre-175mm`` style fragments and query strings."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def category_of(url: str) -> str | None:
    """Return the category slug of a product URL, or None if it is not one."""
    match = re.search(rf"/{LANG}/([^/]+)/\d+[^/]*\.html$", url)
    return match.group(1) if match else None


def sitemap_products(cache: Cache, force: bool = False) -> list[str]:
    """Every ``/en/`` product URL the shop publishes, in sitemap order."""
    entry = cache.fetch(SITEMAP_URL, force=force)
    urls = [clean_product_url(u) for u in LOC_RE.findall(entry.text())]
    return [u for u in urls if category_of(u)]


def scope(products: list[str], categories: list[str]) -> dict[str, list[str]]:
    wanted = set(categories)
    result: dict[str, list[str]] = {c: [] for c in categories}
    for url in products:
        category = category_of(url)
        if category in wanted and url not in result[category]:
            result[category].append(url)
    return result


def crawl(
    cache: Cache, categories: list[str], force: bool, dry_run: bool
) -> dict[str, list[str]]:
    products = sitemap_products(cache, force=force)
    print(f"sitemap: {len(products)} product pages published")

    result = scope(products, categories)
    for category in categories:
        print(f"  {category:32} {len(result[category]):3}")
    total = sum(len(v) for v in result.values())
    print(f"\n{total} product pages in scope")

    if dry_run:
        return result

    done = 0
    for category, urls in result.items():
        for url in urls:
            entry = cache.fetch(url, force=force)
            done += 1
            origin = "cache" if entry.from_cache else "network"
            print(f"  [{done:3}/{total}] [{origin}] {entry.status} {url}", flush=True)
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
    crawl(cache, categories, args.force, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
