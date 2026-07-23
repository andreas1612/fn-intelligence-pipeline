"""Run all collectors. Health-checks each source: a zero-item fetch or a fetch
error is reported and makes the run exit non-zero, so a silently broken feed is
visible rather than passing as a quiet no-op.

    python -m src.run
"""
from __future__ import annotations

import sys

from . import config
from .collectors import cy_tax, cysec, html_list
from .collectors.base import collect_source
from .db import connect, counts, init_db

# Bespoke per-source scrapers (kind: scrape, no `scraper` key). Config-driven
# sites use scraper: html_list. RSS sources use the generic collector.
SCRAPERS = {"cysec": cysec.collect, "cy_tax": cy_tax.collect}


def _collect(conn, src):
    if src.get("kind") == "scrape":
        if src.get("scraper") == "html_list":
            return html_list.collect(conn, src)
        handler = SCRAPERS.get(src["key"])
        if not handler:
            raise RuntimeError(f"no scraper registered for '{src['key']}'")
        return handler(conn, src)
    return collect_source(conn, src)


def main() -> int:
    conn = connect()
    init_db(conn)

    sources = config.load_sources()
    results, failures = [], []

    for src in sources:
        try:
            stats = _collect(conn, src)
            results.append(stats)
            flag = "  <-- ZERO ITEMS" if stats["seen"] == 0 else ""
            print(f"[{stats['category']:9}] {stats['source']:20} "
                  f"seen={stats['seen']:4} new={stats['new']:4} "
                  f"newest={stats['newest']}{flag}")
            if stats["seen"] == 0:
                failures.append(f"{src['key']}: zero items")
        except Exception as e:
            print(f"[FAIL] {src['key']:20} {type(e).__name__}: {e}")
            failures.append(f"{src['key']}: {e}")

    c = counts(conn)
    print(f"\nDB totals: items={c['items']} triaged={c['triaged']} routed={c['routed']}")
    conn.close()

    if failures:
        print(f"\n{len(failures)} source(s) unhealthy:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nAll sources healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
