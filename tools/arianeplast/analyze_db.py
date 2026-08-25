"""Audit the Arianeplast entries in data/ — inventory, duplicates, consistency.

Reads only the repository, never the network.

    python tools/arianeplast/analyze_db.py
    python tools/arianeplast/analyze_db.py --brand arianeplast
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

# French colour/finish words seen in the Arianeplast entries and their English
# equivalent. Used only to detect duplicate pairs across the two languages.
FR_EN = {
    "aluminium": "aluminum",
    "argent": "silver",
    "blanc": "white",
    "bonbon": "candy",
    "bleu": "blue",
    "ciel": "sky",
    "corail": "coral",
    "cuivre": "copper",
    "fluo": "fluorescent",
    "gris": "gray",
    "grey": "gray",
    "huitre": "oyster",
    "jaune": "yellow",
    "kaki": "khaki",
    "marron": "brown",
    "metallique": "metallic",
    "metallise": "metallic",
    "moule": "mussel",
    "nacre": "pearl",
    "noir": "black",
    "ocre": "ochre",
    "ocher": "ochre",
    "peau": "skin",
    "peche": "peach",
    "perle": "pearl",
    "pistache": "pistachio",
    "pomme": "apple",
    "rose": "pink",
    "rouge": "red",
    "translucide": "translucent",
    "vert": "green",
    "violet": "purple",
}

# Resin-grade / colour-reference tokens: they say which pellet or colour chart
# was used, not which product it is, so they must not separate two entries.
GRADE_TOKENS = {"4043d", "pantone", "pla", "ral"}

# Words from FR_EN that are French and nothing else. "rose", "violet", "grey",
# "ocher", "orange" also exist in English, so they say nothing about the
# language of a name and are excluded here.
FRENCH_ONLY = {
    "aluminium",
    "argent",
    "blanc",
    "bleu",
    "bonbon",
    "ciel",
    "corail",
    "cuivre",
    "fluo",
    "gris",
    "huitre",
    "jaune",
    "kaki",
    "marron",
    "metallique",
    "metallise",
    "moule",
    "nacre",
    "noir",
    "ocre",
    "peau",
    "peche",
    "perle",
    "pistache",
    "pomme",
    "rouge",
    "translucide",
    "vert",
}

VISUAL_HINTS = {
    "silk": "silk",
    "translucent": "translucent",
    "translucide": "translucent",
}


def ascii_fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", ascii_fold(name).lower()) if t]


def normalized_name(name: str) -> str:
    """Language- and grade-independent key for a material name."""
    toks = [FR_EN.get(t, t) for t in tokens(name) if t not in GRADE_TOKENS]
    return " ".join(sorted(set(toks)))


def french_words(name: str) -> list[str]:
    """French words left in an otherwise English name."""
    return [t for t in tokens(name) if t in FRENCH_ONLY]


def expected_slug(brand: str, name: str) -> str:
    base = ascii_fold(name).lower().replace("+", "")
    return f"{brand}-" + re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def load(brand: str) -> list[dict]:
    materials = []
    for path in sorted((REPO / "data" / "materials" / brand).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["_path"] = path.relative_to(REPO)
        materials.append(data)
    return materials


def section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", default="arianeplast")
    args = parser.parse_args()
    brand = args.brand

    materials = load(brand)
    packages = list((REPO / "data" / "material-packages" / brand).glob("*.yaml"))

    print(f"Arianeplast audit — {len(materials)} materials, {len(packages)} packages")

    section("Inventory by type")
    by_type = Counter(f"{m.get('class')} / {m.get('type')}" for m in materials)
    for key, count in by_type.most_common():
        print(f"  {key:20s} {count}")

    section("Inventory by source category (spool format in the product URL)")
    by_category: Counter[str] = Counter()
    for m in materials:
        match = re.search(r"arianeplast\.com/[a-z]{2}/([a-z0-9-]+)/", m.get("url", ""))
        by_category[match.group(1) if match else "(unparsed)"] += 1
    for key, count in by_category.most_common():
        print(f"  {key:20s} {count}")

    section("Duplicates — same product under two names")
    groups: dict[str, list[dict]] = defaultdict(list)
    for m in materials:
        groups[normalized_name(m["name"])].append(m)
    duplicates = {k: v for k, v in sorted(groups.items()) if len(v) > 1}
    if not duplicates:
        print("  none")
    for key, group in duplicates.items():
        print(f"  [{key}]")
        for m in group:
            color = (m.get("primary_color") or {}).get("color_rgba", "-")
            print(f"     {m['slug']:44s} {m['name']:28s} {color}  {m['url']}")

    section("Untranslated names (French kept instead of English)")
    french = [(m, french_words(m["name"])) for m in materials]
    french = [(m, w) for m, w in french if w]
    for m, words in french:
        print(f"  {m['slug']:44s} {m['name']:32s} ({', '.join(words)})")
    print(f"  → {len(french)} of {len(materials)}")

    section("Competing English spellings for the same word")
    variants = [("gray", "grey"), ("ochre", "ocher"), ("aluminum", "aluminium")]
    for a, b in variants:
        users = {
            w: [m["name"] for m in materials if w in tokens(m["name"])] for w in (a, b)
        }
        if users[a] and users[b]:
            for w, names in users.items():
                print(f"  {w:10s} {', '.join(names)}")
            print()

    section("Slug does not match the name")
    for m in materials:
        want = expected_slug(brand, m["name"])
        if want != m["slug"]:
            print(f"  {m['slug']:44s} name={m['name']!r} → {want}")

    section("Colour codes shared by different products")
    by_color: dict[str, list[str]] = defaultdict(list)
    for m in materials:
        color = (m.get("primary_color") or {}).get("color_rgba")
        if color:
            by_color[color].append(m["name"])
    for color, names in sorted(by_color.items()):
        if len(names) > 1:
            print(f"  {color}  {', '.join(names)}")
    missing = [m["slug"] for m in materials if not (m.get("primary_color") or {}).get("color_rgba")]
    if missing:
        print(f"  no primary_color: {', '.join(missing)}")

    section("URL hygiene")
    for m in materials:
        url = m.get("url", "")
        problems = []
        if "/fr/" in url:
            problems.append("French locale")
        if "#" in url:
            problems.append("fragment")
        if problems:
            print(f"  {m['slug']:44s} {', '.join(problems)}")
            print(f"      {url}")

    section("Tag consistency")
    for m in materials:
        name = m["name"].lower()
        tags = set(m.get("tags") or [])
        for hint, tag in VISUAL_HINTS.items():
            if hint in name and tag not in tags:
                print(f"  {m['slug']:44s} name says {hint!r} but no {tag!r} tag")
    metallic = [
        m
        for m in materials
        if re.search(r"metallic|metallis|pearl|nacre", ascii_fold(m["name"]).lower())
        and not (set(m.get("tags") or []) & {"pearlescent", "iridescent", "imitates_metal", "glitter"})
    ]
    for m in metallic:
        print(f"  {m['slug']:44s} metallic/pearl finish with no visual tag")

    section("Properties coverage")
    filled = [m for m in materials if m.get("properties")]
    print(f"  materials with a non-empty properties block: {len(filled)}/{len(materials)}")
    print(f"  material packages (spools, GTINs): {len(packages)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
