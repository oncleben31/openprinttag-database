"""Reconcile the crawled Arianeplast listings with what the database holds.

`extract.py` yields one record per *listing*, and Arianeplast lists the same
filament once per spool format. This module regroups those listings into
products, lines each product up against the entries already in
`data/materials/arianeplast/`, and reports what the database is missing, what it
holds under a name the shop no longer uses, and what it holds twice.

It writes nothing to `data/`. Its output is a report to be read and argued with
before any of it is applied.

    python tools/arianeplast/reconcile.py --records extracted.yaml
    python tools/arianeplast/reconcile.py --records extracted.yaml --format yaml

The grouping key is the product's URL slug with the shop's boilerplate removed
(brand name, spool format, "made in France", the numeric product id, an EAN
occasionally glued to the slug). Two listings that reduce to the same key are
the same filament in two formats. The key is a heuristic and is printed in the
report so it can be checked.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_db import french_words  # noqa: E402

MATERIALS_DIR = Path("data/materials/arianeplast")

# Categories whose products the shop itself files under PLA. Used only when a
# product's data sheet omits the Material row.
PLA_CATEGORY_RE = re.compile(r"^(?:pla-|refill-pla|3d-filaments-pla)", re.I)

# Tokens the shop repeats in every product slug and title, which say nothing
# about which filament it is.
BOILERPLATE = {
    "filament", "filaments", "fil", "fils", "bobine", "bobines", "spool", "spools",
    "imprimante", "printer", "3d", "pla", "plus", "arianeplast", "marque", "brand",
    "fabrique", "fabrique-en-france", "made", "in", "france", "en", "de", "du", "des",
    "la", "le", "les", "pour", "the", "for", "and", "with", "kg", "g", "m",
    "recharge", "refill", "sans", "without",
}

# Spool-format tokens: they belong to the package, not to the material.
FORMAT_TOKEN_RE = re.compile(
    r"^(?:\d+(?:[.,]\d+)?(?:kg|g|m)|format|\d+)$", re.I
)

MATERIAL_PREFIX_RE = re.compile(r"^\s*(?:filament\s+)?pla\s*\+?\s*", re.I)

# Boilerplate the shop repeats in its titles. Only wording that says nothing
# about which filament it is: anything that could be part of a product name
# (Silk, Diffusing, Interferential…) is left alone.
TITLE_NOISE_RE = re.compile(
    r"""(?ix)
    (?:
        \b(?:made|manufactured|fabriqu[ée]s?)\s+in\s+france\b |
        \b(?:made|manufactured|fabriqu[ée]s?)\s+in\b |
        \bfabriqu[ée]s?\s+en\s+france\b |
        \bfor\s+3d\s+print(?:er|ing)?\b | \bimpression\s+3d\b |
        \b3d\s*filaments?\b | \bfilaments?\s*3d\b | \bfilaments?\b |
        \bfil\s+pour\b | \bbobines?\b | \bspools?\b |
        \barianeplast\b | \bmarque\b | \bbrand\b |
        \b\d+(?:[.,]\d+)?\s*(?:kg|g|m|mm)\b |
        \bpar\b
    )
    """,
)


def slug_key(url: str) -> str:
    """Reduce a product URL to something stable across spool formats."""
    slug = url.rsplit("/", 1)[-1].removesuffix(".html")
    slug = re.sub(r"^\d+-", "", slug)          # leading product id
    slug = re.sub(r"\b\d{8,14}\b", "", slug)   # EAN glued into some slugs
    tokens = [
        t
        for t in re.split(r"[-_]+", slug)
        if t and t.lower() not in BOILERPLATE and not FORMAT_TOKEN_RE.match(t)
    ]
    return " ".join(tokens)


def clean_title(name_en: Optional[str]) -> Optional[str]:
    """The shop's English title, minus the boilerplate around the product name."""
    if not name_en:
        return None
    text = TITLE_NOISE_RE.sub(" ", name_en)
    text = re.sub(r"\s*[-–]\s*(?=[-–]|$)", " ", text)   # dashes left by the cuts
    text = re.sub(r"[\s,]+", " ", text).strip(" -–,")
    return text or None


def english_source(record: dict) -> tuple[Optional[str], str]:
    """Pick the shop string to name this product from, and say which one it is.

    The shop translates unevenly: the product name is English for some products
    and French for others, and the meta title is English but truncated. Prefer a
    product name with no French left in it, fall back to an untruncated meta
    title, then to a truncated one. When only French is on offer, return None —
    the caller reports it rather than translating on the shop's behalf.
    """
    name = record.get("name")
    meta = record.get("meta_title")
    if name and not french_words(name):
        return name, "name"
    if meta and not french_words(meta):
        return meta, "meta_title" + ("_truncated" if record.get("meta_title_truncated") else "")
    return None, "french_only"


def proposed_material_name(record: dict) -> tuple[Optional[str], str]:
    """'PLA+ red RAL 3020 Arianeplast 1kg made in France' -> 'PLA+ Red RAL 3020'.

    The wording stays the shop's own: only the boilerplate is dropped and the
    colour words are capitalised, to match the convention the other entries
    already follow. Acronyms and colour references (RAL, Pantone, 4043D) keep
    the case the shop gives them.
    """
    source_text, source = english_source(record)
    cleaned = clean_title(source_text)
    if not cleaned:
        return None, source
    cleaned = MATERIAL_PREFIX_RE.sub("", cleaned).strip()
    words = []
    for word in cleaned.split():
        if word.isupper() or any(c.isdigit() for c in word):
            words.append(word)          # RAL, 3020, 4043D, 3268C
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return ("PLA+ " + " ".join(words)).strip(), source


def is_pla(record: dict) -> tuple[Optional[bool], str]:
    """Whether this product is a PLA, and on whose word.

    The data sheet's Material row is the answer when there is one. A fair number
    of the older products have no such row; for those the shop's own category is
    the next best evidence, and the report says so rather than hiding it.
    """
    material = (record.get("material_stated") or "").strip()
    if material:
        return material.upper().startswith("PLA"), "data_sheet"
    category = record.get("category") or ""
    if PLA_CATEGORY_RE.match(category):
        return True, "category"
    return None, "unstated"


def load_db() -> list[dict]:
    entries = []
    for path in sorted(MATERIALS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["_path"] = str(path)
        entries.append(data)
    return entries


def strip_fragment(url: str) -> str:
    return re.sub(r"[#?].*$", "", url or "")


def reconcile(records: list[dict]) -> dict[str, Any]:
    listings = [r for r in records if not r.get("http_status")]
    unreachable = [r for r in records if r.get("http_status")]

    pla, not_pla, unknown = [], [], []
    for record in listings:
        verdict, source = is_pla(record)
        record["_pla_source"] = source
        (pla if verdict else not_pla if verdict is False else unknown).append(record)

    groups: dict[str, list[dict]] = defaultdict(list)
    for record in pla:
        groups[slug_key(record["url"])].append(record)

    db = load_db()
    db_by_url = {strip_fragment(e.get("url", "")): e for e in db}
    db_by_key = defaultdict(list)
    for entry in db:
        db_by_key[slug_key(strip_fragment(entry.get("url", "")))].append(entry)

    products = []
    for key, items in sorted(groups.items()):
        matched = {
            id(e): e
            for item in items
            for e in ([db_by_url[item["url"]]] if item["url"] in db_by_url else [])
        }
        for entry in db_by_key.get(key, []):
            matched[id(entry)] = entry
        entries = list(matched.values())
        ordered = sorted(items, key=lambda i: i.get("net_weight_g") or 0)
        # Name the product from whichever of its listings the shop translated.
        named = [proposed_material_name(i) for i in ordered]
        best = next(
            (n for n, s in named if n and s == "name"),
            next((n for n, s in named if n), None),
        )
        source = next(
            (s for n, s in named if n and s == "name"),
            next((s for n, s in named if n), "french_only"),
        )
        products.append(
            {
                "key": key,
                "listings": [
                    {
                        "url": i["url"],
                        "category": i.get("category"),
                        "sku": i.get("sku"),
                        "gtin": i.get("gtin"),
                        "net_weight_g": i.get("net_weight_g"),
                        "filament_diameter_um": i.get("filament_diameter_um"),
                        "name": i.get("name"),
                        "meta_title": i.get("meta_title"),
                        "color_family": i.get("color_family"),
                        "effect": i.get("effect"),
                        "pla_source": i.get("_pla_source"),
                        "properties": i.get("properties"),
                    }
                    for i in ordered
                ],
                "color_family": next(
                    (i.get("color_family") for i in ordered if i.get("color_family")), None
                ),
                "effect": next((i.get("effect") for i in ordered if i.get("effect")), None),
                "proposed_name": best,
                "proposed_name_source": source,
                "db_entries": [
                    {"slug": e.get("slug"), "name": e.get("name"), "uuid": e.get("uuid")}
                    for e in entries
                ],
            }
        )

    covered = {e["slug"] for p in products for e in p["db_entries"]}
    orphans = [
        {"slug": e.get("slug"), "name": e.get("name"), "url": e.get("url")}
        for e in db
        if e.get("slug") not in covered
    ]

    return {
        "summary": {
            "listings_crawled": len(records),
            "listings_unreachable": len(unreachable),
            "listings_pla": len(pla),
            "listings_not_pla": len(not_pla),
            "listings_material_unstated": len(unknown),
            "products": len(products),
            "products_absent_from_db": sum(1 for p in products if not p["db_entries"]),
            "products_duplicated_in_db": sum(
                1 for p in products if len(p["db_entries"]) > 1
            ),
            "db_entries": len(db),
            "db_entries_unmatched": len(orphans),
            "products_named_from_french_only": sum(
                1 for p in products if p["proposed_name_source"] == "french_only"
            ),
        },
        "not_pla": [
            {"url": r["url"], "material": r.get("material_stated")} for r in not_pla
        ],
        "material_unstated": [{"url": r["url"], "name": r.get("name")} for r in unknown],
        "unreachable": [{"url": r["url"], "status": r["http_status"]} for r in unreachable],
        "products": products,
        "db_entries_unmatched": orphans,
    }


def print_report(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("Arianeplast reconciliation")
    print("=" * 60)
    for label, value in summary.items():
        print(f"  {label:32} {value}")

    if result["not_pla"]:
        print(f"\nNot PLA, per the shop's own data sheet ({len(result['not_pla'])})")
        for row in result["not_pla"][:20]:
            print(f"  {row['material']:12} {row['url']}")

    if result["material_unstated"]:
        print(f"\nData sheet states no material ({len(result['material_unstated'])})")
        for row in result["material_unstated"][:20]:
            print(f"  {row['url']}")

    absent = [p for p in result["products"] if not p["db_entries"]]
    print(f"\nProducts online but absent from the database ({len(absent)})")
    for product in absent:
        formats = ", ".join(
            f"{l['net_weight_g']}g" if l["net_weight_g"] else "?"
            for l in product["listings"]
        )
        print(f"  {product['proposed_name'] or product['key']:44} [{formats}]")

    duplicated = [p for p in result["products"] if len(p["db_entries"]) > 1]
    print(f"\nProducts the database holds more than once ({len(duplicated)})")
    for product in duplicated:
        print(f"  {product['proposed_name'] or product['key']}")
        for entry in product["db_entries"]:
            print(f"      {entry['slug']:44} {entry['name']}")

    renames = [
        p
        for p in result["products"]
        if len(p["db_entries"]) == 1
        and p["proposed_name"]
        and p["db_entries"][0]["name"] != p["proposed_name"]
    ]
    print(f"\nNames that differ from the shop's English title ({len(renames)})")
    for product in renames:
        print(f"  {product['db_entries'][0]['name']:40} -> {product['proposed_name']}")

    if result["db_entries_unmatched"]:
        print(
            f"\nDatabase entries matching no online listing "
            f"({len(result['db_entries_unmatched'])})"
        )
        for entry in result["db_entries_unmatched"]:
            print(f"  {entry['slug']:44} {entry['name']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True, help="YAML written by extract.py")
    parser.add_argument("--format", choices=["text", "yaml"], default="text")
    parser.add_argument("-o", "--output", help="write the YAML report here")
    args = parser.parse_args()

    records = yaml.safe_load(Path(args.records).read_text(encoding="utf-8"))
    result = reconcile(records)

    if args.format == "yaml" or args.output:
        text = yaml.safe_dump(result, sort_keys=False, allow_unicode=True, width=100)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"report -> {args.output}")
        else:
            sys.stdout.write(text)
    else:
        print_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
