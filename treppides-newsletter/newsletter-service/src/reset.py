"""Testing helper: reset state so a test cycle can start clean.

Production is deliberately idempotent (dedup + untriaged-only) so it can run
forever without re-spending. That same stickiness gets in the way while TESTING,
where you want to re-run the whole pipeline repeatedly. This wipes state on demand.

    python -m src.reset --routes --yes     # clear routing only (re-match is free)
    python -m src.reset --triage --yes      # clear triage + routes (re-triage SPENDS)
    python -m src.reset --all --yes         # wipe everything: items, triage, routes, sync

Nothing here is ever used in production. --yes is required to actually delete.
"""
from __future__ import annotations

import argparse
import sys

from .db import connect, init_db


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="wipe items, triage, routes, sync_state")
    ap.add_argument("--triage", action="store_true", help="clear triage results + routes (keep items)")
    ap.add_argument("--routes", action="store_true", help="clear routes only")
    ap.add_argument("--yes", action="store_true", help="confirm the deletion")
    args = ap.parse_args()

    if not (args.all or args.triage or args.routes):
        print("Nothing to do. Pass --all, --triage, or --routes (and --yes).")
        return 1

    conn = connect()
    init_db(conn)

    if not args.yes:
        # Dry run: report what would be deleted.
        c = conn.execute("SELECT COUNT(*) c FROM items").fetchone()["c"]
        r = conn.execute("SELECT COUNT(*) c FROM routes").fetchone()["c"]
        scope = "everything (items+triage+routes+sync)" if args.all else (
            "triage+routes" if args.triage else "routes")
        print(f"DRY RUN - would clear {scope}. items={c} routes={r}. "
              f"Re-run with --yes to apply.")
        return 0

    if args.all:
        conn.execute("DELETE FROM routes")
        conn.execute("DELETE FROM items")
        conn.execute("DELETE FROM sync_state")
        print("Wiped items, routes, sync_state. Next `run` collects fresh.")
    elif args.triage:
        conn.execute("DELETE FROM routes")
        conn.execute(
            "UPDATE items SET triaged_at=NULL, theme_tags=NULL, jurisdiction=NULL, "
            "doc_type=NULL, level=NULL, confidence=NULL, ai_summary=NULL, "
            "archived=0, model=NULL, input_tokens=NULL, output_tokens=NULL"
        )
        print("Cleared triage + routes. Next `triage` re-tags (this spends credits).")
    elif args.routes:
        conn.execute("DELETE FROM routes")
        print("Cleared routes. Next `match` re-routes (free).")

    conn.commit()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
