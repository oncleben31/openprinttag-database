# Arianeplast — what the manufacturer actually states

Evidence gathered from arianeplast.com for the OpenPrintTag entries. Every line
here has a source on the manufacturer's own site; anything the site does not
state is listed under [Not stated anywhere](#not-stated-anywhere) rather than
filled in from elsewhere.

Sources: 344 product pages (English), the English sitemap, and six technical
datasheets linked from the product pages. Cached under `.cache/arianeplast/`,
regenerate with `crawl.py` then `extract.py`.

## The catalogue, as of the crawl

| | |
|---|---|
| Product pages published (sitemap) | 636 |
| Fetched — the PLA-plausible categories | 344 |
| PLA listings | 319 |
| …grouping into distinct products | **139** |
| Entries currently in `data/materials/arianeplast/` | 78 |
| Products online but absent from the database | 61 |
| Products the database holds twice | 6 |
| Database entries with no matching listing | 2 |

Set aside, with the reason: 15 listings the shop's data sheet says are not PLA
(PETG, ABS, TPU, PCTG, PC, PMMA, PA6/PA12, PS, photopolymer resin), 5 multi-spool
packs, and 5 laser-marking filaments whose polymer the site never names.

The 139 products break down by how many formats each is listed in: 65 in one
format, 15 in two, 22 in three, 27 in four, 10 in five. A product listed five
times is one colour sold as a 10 m sample, a 1 kg spool, a 1 kg spool-less
refill, a 2.3 kg and an 8 kg spool — one `Material`, several `MaterialPackage`.

## Where each field comes from

Every product page embeds the shop's own PrestaShop product object in
`data-product="…"`. It carries, per listing:

| Field | Source | Coverage |
|---|---|---|
| `gtin` | `attributes[].ean13`, also the data sheet's `ean13` row | 243/319 |
| `nominal_netto_full_weight` | data sheet, `Net Weight` row | 272/319 |
| `filament_diameter` | data sheet, `Diameter` row | 304/319 |
| `brand_specific_id` | `reference` (the shop's SKU) | ~all |
| `url` | `link`, canonical `/en/` form | all |
| print temperatures | product description text | 271/319 |
| colour / finish | data sheet, `Color Family` and `Effect` rows | most |

The 47 listings with no net weight are the 24 ten-metre samples plus 23 others
whose data sheet omits the row. **`nominal_netto_full_weight` is required by the
schema**, so a 10 m sample cannot be expressed as a `MaterialPackage` without a
weight the manufacturer does not publish.

## PLA+ technical datasheet (TEC-PLA-001 rev. 1.0, 8 August 2026)

Linked from 240 of the 344 product pages, so it covers the bulk of the range.

| | |
|---|---|
| Nozzle temperature | 190 – 230 °C |
| Bed temperature | not required; 50 – 70 °C depending on machine and part |
| Diameters | 1.75 mm and 2.85 mm, tolerance ± 0.03 mm |
| Packagings | 500 g, 1 kg, 2.3 kg, 8 kg spools |
| Density | 1.24 g/cm³ (ASTM D792) |
| Melting point | 145 – 160 °C · glass transition 55 – 60 °C |
| Base resin | polylactic acid, from renewable plant resources; pellets from the USA |
| Colour masterbatch | 3 % by mass, French origin |
| Filled ranges | compounds with 30 % micronised **oyster or mussel shell** powder, French sourced, ground to 250 µm — **a 0.5 mm nozzle minimum is required** |
| Food contact | explicitly not suitable |

Two things this settles:

* **`pla-moule` is mussel shell, not a mould.** The handoff left this open; the
  datasheet names the "oyster or mussel shell powder" ranges outright, and
  `PLA+ Oyster` is its sibling.
* **The PLA+ range is not documented as compostable.** Section 9 covers safety
  and environment and says nothing about composting — only Citeo packaging EPR.
  The database currently carries `industrially_compostable` on **77 of its 78
  entries**. Across all 344 crawled pages, only two mention composting at all.
  What the datasheet does support is `bio_based`.

## Other ranges

| Range | Datasheet says |
|---|---|
| **PLA Eco** | "biodégradable et compostable", certified **EN 13432**, certificates from DIN Certco, Vinçotte and BPI. Density 1.36–1.40 g/cm³, melt 140–155 °C. This is the range `industrially_compostable` belongs to. |
| **PLA Carbon** | Print 195 – 210 °C, drying 60 °C, brass nozzle, density 1.26 g/cm³, PFAS-free, bio-based polymer |
| **Wood** | Contains wood fibres, bio-based carbon content > 75 %, melting > 155 °C. No print temperature given — the product pages have it. |
| **Cork** | Contains cork fibres. The product text adds: 30 % cork powder, 70 % PLA, Ingeo 4043D resin, thick layers (0.25–0.3 mm) advised, no heated bed needed. |
| **Bamboo** | Contains bamboo fibres, density 1.19 g/cm³ |

## Naming, as the shop writes it

The shop translates unevenly, and the handoff's assumption that the `<h1>` holds
the English name does not hold:

* the product name (`<h1>`) is English for some products and French for others;
* the meta title (`<title>`) is English but **truncated at about 70 characters**,
  frequently mid-SKU;
* the data-sheet rows `Color Family` and `Effect` are English, short and
  consistent — the only reliable English strings on the page.

13 products have no English name anywhere on the site.

The same product is also worded differently from one format to the next — "RAL
3020" / "RAL3020" / nothing, a stray "3D", a "fil" or "bobine de fil" prefix on
most 2.3 kg listings, "Metal" in the refills where the spools say "métallisé".
None of it identifies the filament, and `reconcile.py` keeps it out of the
identity key. Pantone references are kept: `PLA+ Green` and
`PLA+ Green Pantone 3268C` are two products.

## Not stated anywhere

* **RGB / hex colour values.** The site publishes no colour codes — only the
  `Color Family` word and product photos. The four conflicting colour pairs
  flagged in `merge_plan.yaml` therefore cannot be settled from the site, and
  neither can the ten suspicious hex values shared by distinct products. The
  values currently in the database appear to have been picked off photographs.
* **Drying temperature and time** for the PLA+ range (the carbon datasheet gives
  60 °C, the others say nothing).
* **The polymer of the five laser-marking filaments.**
* **A weight for the 10 m samples.**

## Session 4 (2026-08-28) — filling gaps from issue #32

Targeted fetches (not a full re-crawl) for the products listed in
[issue #32](https://github.com/oncleben31/openprinttag-database/issues/32).

* **PLA Though+ / Ingeo 3D870 range added** (10 materials, category
  `ingeo-3d870`, "PLA TOUGH + - Ingeo 3d870" on the site). Every one of the ten
  product pages carries a stale top-level `Net Weight`/`Diameter` feature
  (`8kg`/`2.85mm` or `2.3kg`) that does not match the only real, purchasable
  attribute combination on the page (`1 kg`, `1.75mm`, with its own GTIN). The
  attribute combination was trusted over the feature table for all ten —
  it is what actually carries the GTIN and price. No colour codes are
  published for this range, same as the rest of the catalogue.
  Print temperature (210–230 °C) comes from the shared description text; the
  bed temperature is stated once, as a single value ("Tray: 50°"), not a
  range — recorded as `min_bed_temperature: max_bed_temperature: 50` rather
  than left out, since the page does give an exact number.
* **PETG Metallic Interferential Blue was crawled but not added** — pulled
  back out at the user's request after review, before commit. The page (id
  2564, GTIN `3760349160786`) shows the same stale-feature-vs-attribute
  conflict as the Ingeo range above (feature says `2.3kg`, the one real
  attribute says `1 kg`), and its refill (id 5096, GTIN `3760349166337`) is
  still listed in issue #32 as missing. Left for a future pass.
* **`arianeplast-pla-bamboo` (660g vs 2000g) — unresolved GTIN conflict.**
  The live product page for id 399 ("bambou 660g ou 2kg") now exposes a
  single sellable attribute: `660g`, GTIN `3770008753921`. The database
  already carried a `2000g` package for the same product under a different
  GTIN (`3760276362000`), from the session-3 crawl. Rather than overwrite
  that entry on a guess, a second package (`arianeplast-pla-bamboo-660g`)
  was added alongside it, per the user's explicit call — so the material now
  carries two packages whose GTINs both come from the same product ID at
  different points in time. Worth a fresh crawl of this one product later to
  see whether the 2kg variant has actually been discontinued.
* **`PLA Multicolor 350g` (id 5281) — title/body mismatch.** The page title
  says "PLA + Multicolor", the body text says "Multicolor Pla Basic". Filed
  under the title reading, i.e. `arianeplast-pla-multicolor` (the 5-colour
  gradient, 2300g), per the user's explicit call — not the temperature match,
  which favoured `arianeplast-pla-multicolor-basic` instead.
* **No `brand_specific_id`** on the new `PHA White`/`PHA Black` 1000g
  packages and the multicolor 350g package: their product pages carry no shop
  reference (`blob.reference` is empty), only a PrestaShop numeric product
  ID, which is not a manufacturer SKU.
* `arianeplast-pla-oyster-1000g` (804-pla-huitre) was already in the database
  with a matching GTIN — the issue's link to it was already resolved, no
  change made.
