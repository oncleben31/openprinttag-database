"""Search the cached arianeplast.com pages offline.

Once ``crawl.py`` has filled the cache, every later question about the
manufacturer's data is answered from disk instead of from their server.

    python tools/arianeplast/search_cache.py --list
    python tools/arianeplast/search_cache.py "temp.rature d.extrusion"
    python tools/arianeplast/search_cache.py --url 2626 --dump-text
"""

from __future__ import annotations

import argparse
import html as html_module
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cache import DEFAULT_CACHE_DIR, Cache  # noqa: E402

_SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")


def to_text(html: str) -> str:
    text = _SCRIPT_STYLE.sub(" ", html)
    text = _TAG.sub("\n", text)
    text = html_module.unescape(text)
    lines = [_WS.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pattern", nargs="?", help="regex searched in the page text")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--url", help="only pages whose URL contains this substring")
    parser.add_argument("--list", action="store_true", help="list cached URLs")
    parser.add_argument("--dump-text", action="store_true", help="print the page text")
    parser.add_argument("-C", "--context", type=int, default=1)
    parser.add_argument("-i", "--ignore-case", action="store_true", default=True)
    args = parser.parse_args()

    cache = Cache(args.cache_dir)
    entries = [e for e in cache.entries() if not args.url or args.url in e.url]

    if not entries:
        print(f"cache {args.cache_dir} is empty for this filter — run crawl.py first")
        return 1

    if args.list:
        for entry in entries:
            print(f"{entry.fetched_at:%Y-%m-%d}  {entry.url}")
        print(f"\n{len(entries)} cached pages")
        return 0

    flags = re.I if args.ignore_case else 0
    for entry in entries:
        text = to_text(entry.text())
        if args.dump_text and not args.pattern:
            print(f"===== {entry.url}\n{text}\n")
            continue
        if not args.pattern:
            continue
        lines = text.splitlines()
        hits = [i for i, line in enumerate(lines) if re.search(args.pattern, line, flags)]
        if not hits:
            continue
        print(f"===== {entry.url}")
        shown: set[int] = set()
        for i in hits:
            for j in range(max(0, i - args.context), min(len(lines), i + args.context + 1)):
                if j not in shown:
                    shown.add(j)
                    print(f"  {'>' if j == i else ' '} {lines[j]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
