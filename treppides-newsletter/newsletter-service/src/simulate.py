"""Simulate what a given department (or sub-department) sees in its feed.

This is the dev stand-in for hub identity: instead of resolving the logged-in
user's department from Azure, you pass it explicitly. The eventual hub page shows
exactly this, with the department resolved from /api/me.

    python -m src.simulate --list
    python -m src.simulate --department "Taxation" --sub "VAT"
    python -m src.simulate --department "Technology"
    python -m src.simulate --department "ICAS" --sub "Compliance" --category authority
"""
from __future__ import annotations

import argparse
import json
import sys

from .db import connect
from .match import build_profiles

LEVEL_ORDER = {"Urgent": 0, "High": 1, "Standard": 2, "Low": 3}


def list_departments() -> None:
    seen = []
    for p in build_profiles():
        label = p["department"] + (f" / {p['sub']}" if p["sub"] else "")
        seen.append(label)
    print("Available department feeds:\n")
    for s in seen:
        print(f"  {s}")


def show_feed(department: str, sub: str, category: str | None) -> None:
    conn = connect()
    rows = conn.execute(
        """
        SELECT i.title, i.source, i.source_category, i.level, i.jurisdiction,
               i.doc_type, i.theme_tags, i.ai_summary, i.url, r.matched_on
        FROM routes r JOIN items i ON i.id = r.item_id
        WHERE r.department = ? AND r.subdepartment = ?
        """,
        (department, sub or ""),
    ).fetchall()
    conn.close()

    if category:
        rows = [r for r in rows if r["source_category"] == category]

    rows = sorted(rows, key=lambda r: (LEVEL_ORDER.get(r["level"], 9),
                                       r["source_category"]))

    label = department + (f" / {sub}" if sub else "")
    print(f"\n=== Newsletter feed: {label} "
          f"{'(' + category + ' only)' if category else ''} ===")
    if not rows:
        print("  (no items routed here yet)")
        return

    for section in ("authority", "journal"):
        sec_rows = [r for r in rows if r["source_category"] == section]
        if not sec_rows:
            continue
        heading = "REGULATORY AUTHORITIES" if section == "authority" else "JOURNALS / INDUSTRY NEWS"
        print(f"\n-- {heading} ({len(sec_rows)}) --")
        for r in sec_rows:
            themes = ", ".join(json.loads(r["theme_tags"] or "[]"))
            print(f"\n  [{r['level']}] {r['title']}")
            print(f"      {r['source']} | {r['jurisdiction']} | {r['doc_type']} "
                  f"| themes: {themes}")
            print(f"      why here: {r['matched_on']}")
            if r["ai_summary"]:
                print(f"      {r['ai_summary']}")
            print(f"      {r['url']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--department")
    ap.add_argument("--sub", default="")
    ap.add_argument("--category", choices=["authority", "journal"])
    args = ap.parse_args()

    if args.list or not args.department:
        list_departments()
        return 0
    show_feed(args.department, args.sub, args.category)
    return 0


if __name__ == "__main__":
    sys.exit(main())
