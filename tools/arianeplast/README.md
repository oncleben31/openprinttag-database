# Arianeplast tooling

Helpers used to audit and complete the Arianeplast entries in `data/`. They
touch nothing outside `data/brands/arianeplast.yaml`,
`data/materials/arianeplast/` and `data/material-packages/arianeplast/`.

All scripts run on the repository's own Python (3.12+) and need only `PyYAML`.

## `analyze_db.py` — offline audit

Inventory, duplicate detection and consistency checks over the entries already
in the repository. No network access.

```bash
python tools/arianeplast/analyze_db.py
```

Duplicate detection normalises a material name in two steps: French colour and
finish words are mapped to their English equivalent (`rouge` → `red`,
`métallisé` → `metallic`, …), and resin-grade / colour-chart tokens (`4043D`,
`RAL`, `Pantone`) are dropped, since they identify the pellet or the colour
reference rather than the product. Two entries that normalise to the same key
are the same filament under two names.

## `cache.py` + `crawl.py` — cached, scope-limited scraping

The manufacturer's server must be hit as little as possible, so every request
goes through an on-disk cache:

* one request per URL, ever, until the cache entry expires (30 days by default);
* a minimum delay between two requests (2 s by default);
* a descriptive User-Agent;
* requests to any host other than `arianeplast.com` are refused outright.

The crawl is limited to the product categories named on the command line —
by default the PLA range, which is the scope of the current work.

```bash
# show the scope without making a single request
python tools/arianeplast/crawl.py --dry-run

# fill the cache for the PLA categories
python tools/arianeplast/crawl.py

# another scope later on
python tools/arianeplast/crawl.py --category petg-format-1-kg
```

The cache lives in `.cache/arianeplast/` and is git-ignored: it holds the
manufacturer's raw HTML, which does not belong in this database.

## `search_cache.py` — query the cache offline

Once the cache is filled, every later question is answered from disk.

```bash
python tools/arianeplast/search_cache.py --list
python tools/arianeplast/search_cache.py "print.{0,15}temperature"
python tools/arianeplast/search_cache.py --url 2626- --dump-text
```

## `merge_plan.yaml`

The proposed resolution for the duplicates and the naming inconsistencies found
by `analyze_db.py`. It is a proposal: entries carrying a `verify:` key must be
checked against the manufacturer's English product page before being applied.
