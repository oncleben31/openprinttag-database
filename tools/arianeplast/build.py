"""Write the Arianeplast entries in `data/` from the reconciliation report.

This is the only tool in the directory that writes to `data/`. It takes the
report produced by `reconcile.py` and turns it into `Material` and
`MaterialPackage` files, following the decisions recorded in
`decisions.yaml` next to it.

    python tools/arianeplast/build.py --report report.yaml --dry-run
    python tools/arianeplast/build.py --report report.yaml

Naming policy, in short: an entry already in the database keeps its name unless
that name is actually wrong — French left in it, the brand convention broken, or
a spelling the rest of the brand does not use. Renaming for its own sake is
avoided because `Material::uuid` derives from the name, so every rename churns
the identifier that other databases reference.
"""

from __future__ import annotations

import argparse
import re
import sys
import uuid as uuid_module
from pathlib import Path
from typing import Any, Optional

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_db import ascii_fold, french_words  # noqa: E402
from uuid_utils import (  # noqa: E402
    generate_material_package_uuid,
    generate_material_uuid,
)

BRAND = "arianeplast"
BRAND_UUID = uuid_module.UUID("c4eab185-1ed0-577b-a38d-c7630cf6dd18")

MATERIALS = REPO / "data/materials" / BRAND
PACKAGES = REPO / "data/material-packages" / BRAND
CONTAINERS = REPO / "data/material-containers"

DECISIONS = Path(__file__).resolve().parent / "decisions.yaml"


def load_decisions() -> dict:
    return yaml.safe_load(DECISIONS.read_text(encoding="utf-8"))


def expected_slug(name: str) -> str:
    base = ascii_fold(name).lower().replace("+", "")
    return f"{BRAND}-" + re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def name_needs_fixing(name: str, decisions: dict) -> Optional[str]:
    """Why an existing name must change, or None to leave it alone."""
    if french_words(name):
        return "French wording"
    if not name.startswith(("PLA+ ", "PLA ")):
        return "brand convention is 'PLA[+] <colour>'"
    for wrong, right in decisions["spelling"].items():
        if re.search(rf"\b{wrong}\b", name, re.I):
            return f"the brand spells it {right!r}"
    return None


def apply_spelling(name: str, decisions: dict) -> str:
    for wrong, right in decisions["spelling"].items():
        name = re.sub(rf"\b{wrong}\b", right, name, flags=re.I)
    return name


def material_name(product: dict, decisions: dict) -> tuple[str, str]:
    """The name to use, and how it was arrived at."""
    override = decisions["names"].get(product["key"])
    if override:
        return override["name"], "decisions.yaml"

    existing = [e["name"] for e in product["db_entries"]]
    # For a duplicate pair, the survivor is the entry whose name is English.
    kept = next((n for n in existing if not french_words(n)), None) or (
        existing[0] if existing else None
    )
    if kept:
        reason = name_needs_fixing(kept, decisions)
        if reason is None:
            return kept, "unchanged"
        # The name has to change. The site's own wording, cleaned up, is the
        # starting point; the brand's spellings are then applied to it.
        return apply_spelling(product["proposed_name"] or kept, decisions), reason
    return apply_spelling(product["proposed_name"], decisions), "site"


def reference_listing(product: dict) -> dict:
    """The listing a Material points at: the 1 kg spool when there is one."""
    listings = product["listings"]
    spools = [l for l in listings if (l.get("category") or "").startswith("pla-format")]
    for candidate in (spools or listings):
        if candidate.get("net_weight_g") == 1000:
            return candidate
    return (spools or listings)[0]


def material_tags(product: dict, existing: list[str], decisions: dict) -> list[str]:
    tags = set(existing)
    tags.discard("industrially_compostable")   # not documented for the PLA+ range

    text = " ".join(
        filter(None, [product["proposed_name"] or "", product["key"], product.get("effect") or ""])
    ).lower()
    is_eco = "eco" in product["key"].split()

    tags.add("bio_based")
    if is_eco:
        # The PLA Eco datasheet certifies EN 13432 (DIN Certco, Vinçotte, BPI).
        tags.add("industrially_compostable")
    for pattern, tag in decisions["tags"].items():
        if re.search(rf"\b{pattern}\b", text):
            tags.add(tag)
    return sorted(tags)


def material_properties(product: dict, decisions: dict) -> dict:
    """Print temperatures: the product's own page first, its datasheet second."""
    for listing in product["listings"]:
        if listing.get("properties"):
            return dict(listing["properties"])
    for pattern, values in decisions["datasheet_properties"].items():
        if re.search(rf"\b{pattern}\b", product["key"]):
            return dict(values)
    return dict(decisions["datasheet_properties"]["default"])


def package_slug(material_slug: str, listing: dict) -> str:
    suffix = "-refill" if (listing.get("category") or "").startswith("refill") else ""
    return f"{material_slug}{suffix}-{listing['net_weight_g']}g"


def surviving_entry(product: dict) -> dict:
    """The database entry a merged product inherits from.

    The same one `material_name` keeps: the entry whose name is English. Its
    colour is the one carried over, because the site publishes no colour codes
    at all and the value cannot be recovered from it — see findings.md.
    """
    entries = product["db_entries"]
    if not entries:
        return {}
    return next((e for e in entries if not french_words(e["name"])), entries[0])


def build_material(product: dict, decisions: dict) -> dict[str, Any]:
    name, provenance = material_name(product, decisions)
    existing = surviving_entry(product)
    slug = expected_slug(name)
    entry: dict[str, Any] = {
        "uuid": str(generate_material_uuid(BRAND_UUID, name)),
        "slug": slug,
        "brand": {"slug": BRAND},
        "name": name,
        "class": "FFF",
        "type": "PLA",
        "abbreviation": "PLA",
        "url": reference_listing(product)["url"],
    }
    if existing.get("primary_color"):
        entry["primary_color"] = existing["primary_color"]
    if existing.get("secondary_colors"):
        entry["secondary_colors"] = existing["secondary_colors"]
    entry["tags"] = material_tags(product, existing.get("tags") or [], decisions)
    entry["properties"] = material_properties(product, decisions)
    entry["_provenance"] = provenance
    return entry


def build_packages(material: dict, product: dict, decisions: dict) -> list[dict]:
    packages = []
    for listing in product["listings"]:
        weight = listing.get("net_weight_g")
        if not weight:
            continue        # the schema requires a weight; the shop publishes none
        package: dict[str, Any] = {
            "slug": package_slug(material["slug"], listing),
            "class": "FFF",
            "material": {"slug": material["slug"]},
            "nominal_netto_full_weight": weight,
        }
        if listing.get("gtin"):
            gtin = int(listing["gtin"])
            package["gtin"] = gtin
            package["uuid"] = str(generate_material_package_uuid(BRAND_UUID, gtin))
        if listing.get("sku"):
            package["brand_specific_id"] = listing["sku"]
        is_refill = (listing.get("category") or "").startswith("refill")
        if not is_refill and (CONTAINERS / f"{weight}g.yaml").exists():
            package["container"] = {"slug": f"{weight}g"}
        package["url"] = listing["url"]
        if listing.get("filament_diameter_um"):
            package["filament_diameter"] = listing["filament_diameter_um"]
            package["filament_diameter_tolerance"] = decisions["diameter_tolerance_um"]
        packages.append(package)
    return packages


ORDER = [
    "uuid", "slug", "brand", "name", "class", "type", "abbreviation", "url",
    "primary_color", "secondary_colors", "tags", "properties",
]
PACKAGE_ORDER = [
    "uuid", "slug", "class", "brand_specific_id", "gtin", "material",
    "container", "nominal_netto_full_weight", "filament_diameter",
    "filament_diameter_tolerance", "url",
]


def ordered(entry: dict, order: list[str]) -> dict:
    return {k: entry[k] for k in order if k in entry}


def dump(path: Path, entry: dict, order: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(ordered(entry, order), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def merge_split_groups(products: list[dict], merge_keys: dict[str, str]) -> list[dict]:
    """Fold the groups `decisions.yaml` says are one product into their target."""
    by_key = {p["key"]: p for p in products}
    for source_key, target_key in merge_keys.items():
        source, target = by_key.get(source_key), by_key.get(target_key)
        if source is None or target is None:
            continue
        target["listings"].extend(source["listings"])
        target["db_entries"].extend(
            e for e in source["db_entries"] if e not in target["db_entries"]
        )
        del by_key[source_key]
    return list(by_key.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--materials-only", action="store_true", help="skip the MaterialPackage files"
    )
    args = parser.parse_args()

    report = yaml.safe_load(Path(args.report).read_text(encoding="utf-8"))
    decisions = load_decisions()

    excluded = {e["key"] for e in decisions["exclude"]}
    products = merge_split_groups(report["products"], decisions["merge_keys"])

    kept_materials, written_packages, retired = [], [], []
    for product in products:
        if product["key"] in excluded:
            continue
        material = build_material(product, decisions)
        provenance = material.pop("_provenance")
        kept_materials.append((material, provenance, product))
        if not args.materials_only:
            written_packages.extend(build_packages(material, product, decisions))

    live_slugs = {m["slug"] for m, _, _ in kept_materials}
    # A file is superseded when its product is still online but now lives under
    # another slug — a rename, or a duplicate folded into its twin. A file that
    # matches no listing at all is a different case: the shop has stopped
    # selling it, which is not a reason to drop it from the database.
    superseded = {
        entry["slug"]
        for _, _, product in kept_materials
        for entry in product["db_entries"]
    }
    delisted = []
    for path in sorted(MATERIALS.glob("*.yaml")):
        if path.stem in live_slugs:
            continue
        (retired if path.stem in superseded else delisted).append(path)

    # Two listings reducing to one package slug means the shop contradicts
    # itself about a weight. Keep the first and say so rather than have one
    # silently overwrite the other.
    seen: dict[str, dict] = {}
    conflicts = []
    for package in written_packages:
        if package["slug"] in seen:
            conflicts.append((package, seen[package["slug"]]))
        else:
            seen[package["slug"]] = package
    written_packages = list(seen.values())
    for package, kept in conflicts:
        print(
            f"  conflicting weights for {package['slug']}: kept "
            f"{kept.get('brand_specific_id')}, dropped "
            f"{package.get('brand_specific_id')} ({package['url']})"
        )

    print(f"{len(kept_materials)} materials, {len(written_packages)} packages")
    print(f"{len(retired)} files superseded by a rename or a merge")
    print(f"{len(delisted)} files kept, matching no current listing: "
          + ", ".join(p.stem for p in delisted))
    renamed = [(m, p) for m, p, _ in kept_materials if p not in ("unchanged",)]
    print(f"{len(renamed)} materials named from the site or decisions.yaml")

    if args.dry_run:
        for material, provenance, product in kept_materials:
            existing = product["db_entries"][0]["name"] if product["db_entries"] else "—"
            if provenance != "unchanged":
                print(f"  {existing[:34]:36} -> {material['name'][:38]:40} [{provenance}]")
        for path in retired:
            print(f"  retire {path.name}")
        return 0

    for material, _, _ in kept_materials:
        dump(MATERIALS / f"{material['slug']}.yaml", material, ORDER)
    for package in written_packages:
        dump(PACKAGES / f"{package['slug']}.yaml", package, PACKAGE_ORDER)
    for path in retired:
        path.unlink()
    print("written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
