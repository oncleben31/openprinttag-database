"""Turn cached Arianeplast product pages into structured records.

Every PrestaShop product page carries the shop's own product object, as an
HTML-escaped JSON blob in ``data-product="…"``. It is authoritative and far more
reliable than scraping the rendered page: it holds the reference (SKU), the
per-combination EAN-13, the data-sheet rows the shop calls *features* (Net
Weight, Color Family, Diameter, Material, Effect…), the canonical link and the
description. This module reads that blob, and falls back to the JSON-LD block
and the ``<title>`` for what the blob does not carry.

Nothing here touches the network: it reads what ``crawl.py`` put in the cache.

    # every cached page, as YAML on stdout
    python tools/arianeplast/extract.py -o extracted.yaml

    # a single page, to eyeball the parse
    python tools/arianeplast/extract.py --url 219- --pretty

A note on languages, because the shop is inconsistent about them and this
module deliberately does not paper over it. On an ``/en/`` page:

* ``name`` (the blob's own product name, same string as the ``<h1>``) is
  sometimes English and sometimes still French, product by product;
* ``meta_title`` — the same string as ``<title>`` — is English, but the shop
  truncates it at about 70 characters, often mid-SKU, so it can lose the end of
  the product name;
* the data-sheet rows ``Color Family`` and ``Effect`` are English, short and
  consistent.

All of them are reported as they are, and ``meta_title_truncated`` says whether
the second one was cut. Deciding an English name from these is a judgement call
and is left to the caller.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cache import DEFAULT_CACHE_DIR, Cache  # noqa: E402

DATA_PRODUCT_RE = re.compile(r'data-product="(\{&quot;.*?)"\s', re.S)
LDJSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)

# "Temperature: 200 ° C to 230 ° C", "Temperature heatbed : 60/80 ° C",
# "Température : 195°C à 220°C" — the shop's own wording varies a lot.
DEGREES = r"(\d{2,3})\s*°?\s*C?"
NOZZLE_RE = re.compile(
    rf"temp[ée]?rature\s*(?:d[e']\s*)?(?:buse|extrusion|impression|printing)?\s*:?\s*"
    rf"{DEGREES}\s*(?:to|[àa]|-|/)\s*{DEGREES}",
    re.I,
)
BED_RE = re.compile(
    rf"temp[ée]?rature\s*(?:du\s*)?(?:heatbed|plateau|bed|plate)\s*:?\s*"
    rf"{DEGREES}\s*(?:to|[àa]|-|/)\s*{DEGREES}",
    re.I,
)

WEIGHT_RE = re.compile(r"([\d.,]+)\s*(kg|g)\b", re.I)
DIAMETER_RE = re.compile(r"([\d.,]+)\s*mm", re.I)


def strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def product_blob(page: str) -> Optional[dict]:
    """The shop's own product object, or None when the page has no product."""
    match = DATA_PRODUCT_RE.search(page)
    if not match:
        return None
    raw = html.unescape(match.group(1))
    try:
        value, _ = json.JSONDecoder().raw_decode(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def ld_product(page: str) -> Optional[dict]:
    for block in LDJSON_RE.findall(page):
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("@type") == "Product":
            return value
    return None


def parse_weight_grams(text: str) -> Optional[int]:
    """'1 kg' -> 1000, '315g' -> 315, '2.3kg' -> 2300."""
    match = WEIGHT_RE.search(text or "")
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    return round(value * 1000) if match.group(2).lower() == "kg" else round(value)


def parse_diameter_um(text: str) -> Optional[int]:
    """'1.75mm' -> 1750 (the schema stores micrometres)."""
    match = DIAMETER_RE.search(text or "")
    if not match:
        return None
    return round(float(match.group(1).replace(",", ".")) * 1000)


def parse_temperatures(description: str) -> dict[str, int]:
    """Nozzle and bed ranges, as the product description states them."""
    text = strip_tags(description or "")
    found: dict[str, int] = {}
    bed = BED_RE.search(text)
    if bed:
        low, high = sorted(int(g) for g in bed.groups())
        found["min_bed_temperature"] = low
        found["max_bed_temperature"] = high
    # Run the nozzle pattern on the text with the bed match removed, so that
    # "Temperature heatbed : 60/80" cannot be read as a nozzle range.
    nozzle_text = text[: bed.start()] + text[bed.end() :] if bed else text
    nozzle = NOZZLE_RE.search(nozzle_text)
    if nozzle:
        low, high = sorted(int(g) for g in nozzle.groups())
        found["min_print_temperature"] = low
        found["max_print_temperature"] = high
    return found


TRUNCATION_RE = re.compile(r"\s*(?:\S*\.\.\.|…)\s*$")


def drop_trailing_sku(title: str, sku: Optional[str]) -> str:
    """The shop appends the reference to the meta title: '… made in France FPLAROUGE1KG'."""
    title = title.strip()
    if sku and title.endswith(sku):
        title = title[: -len(sku)].strip()
    return title


def record(url: str, page: str) -> dict[str, Any]:
    """One product page, reduced to the facts this database needs."""
    blob = product_blob(page) or {}
    ld = ld_product(page) or {}
    title = TITLE_RE.search(page)
    h1 = H1_RE.search(page)

    features = {f["name"]: f["value"] for f in blob.get("features") or []}
    combinations = [
        {
            "group": attribute.get("group"),
            "value": attribute.get("name"),
            "reference": attribute.get("reference") or None,
            "gtin": attribute.get("ean13") or None,
        }
        for attribute in (blob.get("attributes") or {}).values()
    ]

    net_weight = parse_weight_grams(features.get("Net Weight", ""))
    diameter = parse_diameter_um(features.get("Diameter", ""))
    if diameter is None and combinations:
        diameter = parse_diameter_um(combinations[0]["value"] or "")

    sku = blob.get("reference") or ld.get("sku") or None
    meta_title = strip_tags(blob.get("meta_title") or "") or (
        strip_tags(title.group(1)) if title else ""
    )
    truncated = bool(TRUNCATION_RE.search(meta_title))
    meta_title = drop_trailing_sku(TRUNCATION_RE.sub("", meta_title), sku)

    return {
        "url": url,
        "category": blob.get("category") or None,
        "category_name": blob.get("category_name") or None,
        "id_product": blob.get("id_product"),
        "name": strip_tags(blob.get("name") or "")
        or (strip_tags(h1.group(1)) if h1 else None),
        "meta_title": meta_title or None,
        "meta_title_truncated": truncated,
        "color_family": features.get("Color Family") or None,
        "effect": features.get("Effect") or None,
        "material_stated": features.get("Material") or None,
        "sku": sku,
        "gtin": (blob.get("ean13") or None)
        or next((c["gtin"] for c in combinations if c["gtin"]), None),
        "net_weight_g": net_weight,
        "filament_diameter_um": diameter,
        "features": features or None,
        "combinations": combinations or None,
        "properties": parse_temperatures(blob.get("description") or "") or None,
        "availability": blob.get("availability") or None,
        "description_short": strip_tags(blob.get("description_short") or "") or None,
        "description": strip_tags(blob.get("description") or "") or None,
        "attachments": [a.get("name") for a in blob.get("attachments") or []] or None,
    }


def records(cache: Cache, url_filter: Optional[str] = None) -> Iterator[dict[str, Any]]:
    for entry in cache.entries():
        if not entry.url.endswith(".html"):
            continue
        if url_filter and url_filter not in entry.url:
            continue
        if entry.status != 200:
            yield {"url": entry.url, "http_status": entry.status}
            continue
        yield record(entry.url, entry.text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--url", help="only pages whose URL contains this substring")
    parser.add_argument("-o", "--output", help="write YAML here instead of stdout")
    parser.add_argument(
        "--pretty", action="store_true", help="print JSON, indented, for one page"
    )
    args = parser.parse_args()

    cache = Cache(args.cache_dir)
    found = list(records(cache, args.url))

    if args.pretty:
        print(json.dumps(found, indent=2, ensure_ascii=False))
        return 0

    import yaml

    text = yaml.safe_dump(found, sort_keys=False, allow_unicode=True, width=100)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"{len(found)} records -> {args.output}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
