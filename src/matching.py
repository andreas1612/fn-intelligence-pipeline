"""Client matching engine.

Matches triaged items to clients by comparing each item's taxonomy tags
(sector, jurisdiction, theme) and level against each client's interest profile
(config/clients.yaml, seeded via src.clients). Fully deterministic: no LLM and
no invented data. Every match records exactly why it matched.

Relevance rule (D-028): an item matches a client only if they share at least one
sector or theme. A shared jurisdiction alone is not a match, because nearly every
item and every client is EU, so jurisdiction-only overlap routed every EU item to
every EU client. Jurisdiction still boosts the score of an item that already
matches on a sector or theme, and is still named in the reason.

Product rule: only human-reviewed items reach clients. By default matching runs
over items with review_status in ('Reviewed', 'Published'), consistent with the
human gate (D-018). Use `preview` to match every triaged item regardless of
review state, for testing against the current backlog; preview never writes.

Level gate: an item matches only if its level is at least as urgent as the
client's min_level (Urgent > High > Standard > Low).

Score weights overlap by dimension: jurisdiction and sector are stronger signals
than theme for regulatory routing.

Table owned here (additive, created if absent):
    matches(item_id, client_id, score, matched_on, created_at, delivered_at)

Idempotent: re-running updates score/matched_on for an (item, client) pair and
never clears delivered_at.

Run with:
    python -m src.matching run
    python -m src.matching preview [--limit N]
    python -m src.matching report
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone

from src import clients as clients_module
from src import db, migrate
from src.collectors.base import logger
from src.triage import LEVELS

# Overlap weights. Jurisdiction and sector route a regulatory item more strongly
# than a shared theme does.
JURISDICTION_WEIGHT = 3.0
SECTOR_WEIGHT = 2.0
THEME_WEIGHT = 1.0

# Rank: lower index is more urgent. An item qualifies for a client when its
# level rank is <= the client's min_level rank.
_LEVEL_RANK = {level: index for index, level in enumerate(LEVELS)}

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    item_id      INTEGER NOT NULL,
    client_id    INTEGER NOT NULL,
    score        REAL NOT NULL,
    matched_on   TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    delivered_at TEXT,
    PRIMARY KEY (item_id, client_id)
);
"""

_SELECT_COLUMNS = (
    "id, level, sector_tags, theme_tags, jurisdiction, title, source, review_status"
)

ELIGIBLE_REVIEWED = f"""
SELECT {_SELECT_COLUMNS} FROM items
WHERE triaged_at IS NOT NULL AND auto_discard IS NULL AND level IS NOT NULL
AND review_status IN ('Reviewed', 'Published')
ORDER BY id
"""

ELIGIBLE_ALL = f"""
SELECT {_SELECT_COLUMNS} FROM items
WHERE triaged_at IS NOT NULL AND auto_discard IS NULL AND level IS NOT NULL
ORDER BY id
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_clients(conn: sqlite3.Connection) -> list[dict]:
    clients = []
    for row in conn.execute("SELECT id, name, min_level FROM clients WHERE active = 1"):
        client_id = row["id"]
        clients.append({
            "id": client_id,
            "name": row["name"],
            "min_level": row["min_level"],
            "sectors": {r[0] for r in conn.execute(
                "SELECT sector_tag FROM client_sectors WHERE client_id = ?", (client_id,))},
            "jurisdictions": {r[0] for r in conn.execute(
                "SELECT jurisdiction_tag FROM client_jurisdictions WHERE client_id = ?", (client_id,))},
            "themes": {r[0] for r in conn.execute(
                "SELECT theme_tag FROM client_themes WHERE client_id = ?", (client_id,))},
        })
    return clients


def _item_tags(row: sqlite3.Row):
    sectors = set(json.loads(row["sector_tags"]) if row["sector_tags"] else [])
    themes = set(json.loads(row["theme_tags"]) if row["theme_tags"] else [])
    jurisdictions = {row["jurisdiction"]} if row["jurisdiction"] else set()
    return sectors, jurisdictions, themes


def _level_ok(item_level, min_level) -> bool:
    if item_level is None:
        return False
    return _LEVEL_RANK.get(item_level, 99) <= _LEVEL_RANK.get(min_level, 99)


def score_match(item_sectors, item_jurisdictions, item_themes, client):
    """Return (score, matched_on) for an item against a client, or None if the
    item shares no sector or theme with the client."""
    shared_j = sorted(item_jurisdictions & client["jurisdictions"])
    shared_s = sorted(item_sectors & client["sectors"])
    shared_t = sorted(item_themes & client["themes"])

    # Relevance requires a shared sector or theme (D-028). Jurisdiction alone is
    # not enough: almost every item and client is EU, so a jurisdiction-only rule
    # sent every EU item to every EU client. A shared jurisdiction still adds to
    # the score below and is named in matched_on when a real match exists.
    if not (shared_s or shared_t):
        return None

    score = (
        JURISDICTION_WEIGHT * len(shared_j)
        + SECTOR_WEIGHT * len(shared_s)
        + THEME_WEIGHT * len(shared_t)
    )

    parts = []
    if shared_j:
        parts.append("jurisdiction: " + ", ".join(shared_j))
    if shared_s:
        parts.append("sector: " + ", ".join(shared_s))
    if shared_t:
        parts.append("theme: " + ", ".join(shared_t))

    return score, "; ".join(parts)


def compute_matches(conn: sqlite3.Connection, preview: bool = False) -> list[dict]:
    clients = _load_clients(conn)
    if not clients:
        logger.warning(
            "no active clients; seed them first with: python -m src.clients seed"
        )
        return []

    sql = ELIGIBLE_ALL if preview else ELIGIBLE_REVIEWED
    results = []
    for item in conn.execute(sql):
        item_sectors, item_jurisdictions, item_themes = _item_tags(item)
        for client in clients:
            if not _level_ok(item["level"], client["min_level"]):
                continue
            scored = score_match(item_sectors, item_jurisdictions, item_themes, client)
            if scored is None:
                continue
            score, matched_on = scored
            results.append({
                "item_id": item["id"],
                "client_id": client["id"],
                "client_name": client["name"],
                "score": score,
                "matched_on": matched_on,
                "title": item["title"],
                "level": item["level"],
                "source": item["source"],
            })
    return results


def _print_preview(results: list[dict]) -> None:
    print("\n--- Match preview (no writes) ---")
    if not results:
        print("No candidate matches. Check that clients are seeded and items are triaged.")
        return
    for r in results:
        print(f"[{r['score']:>4.1f}] item {r['item_id']} [{r['level']}] -> {r['client_name']}")
        print(f"        {(r['title'] or '')[:80]}")
        print(f"        matched on {r['matched_on']}")
    print(f"\n{len(results)} candidate match(es).")


def _print_summary(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT c.name, count(*) AS n, "
        "sum(CASE WHEN m.delivered_at IS NULL THEN 1 ELSE 0 END) AS undelivered "
        "FROM matches m JOIN clients c ON c.id = m.client_id "
        "GROUP BY c.name ORDER BY n DESC"
    ).fetchall()
    print("\n--- Matches by client ---")
    if not rows:
        print("(no matches yet)")
        return
    for row in rows:
        print(f"{row['name']}: {row['n']} match(es), {row['undelivered']} undelivered")


def run(preview: bool = False, limit: int | None = None) -> int:
    conn = db.connect()
    conn.row_factory = sqlite3.Row
    migrate.migrate(conn)
    clients_module.ensure_schema(conn)
    ensure_schema(conn)

    results = compute_matches(conn, preview=preview)

    if preview:
        results.sort(key=lambda r: (-r["score"], r["item_id"], r["client_name"]))
        if limit is not None:
            results = results[:limit]
        _print_preview(results)
        conn.close()
        return 0

    written = 0
    for r in results:
        conn.execute(
            "INSERT INTO matches (item_id, client_id, score, matched_on, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(item_id, client_id) DO UPDATE SET "
            "score = excluded.score, matched_on = excluded.matched_on",
            (r["item_id"], r["client_id"], r["score"], r["matched_on"], now_iso()),
        )
        written += 1
    conn.commit()

    logger.info("matched %d reviewed item-client pair(s)", written)
    _print_summary(conn)
    conn.close()
    return 0


def report() -> int:
    conn = db.connect()
    conn.row_factory = sqlite3.Row
    clients_module.ensure_schema(conn)
    ensure_schema(conn)

    _print_summary(conn)

    print("\n--- Undelivered matches (queue to distribute) ---")
    rows = conn.execute(
        "SELECT c.name AS client, i.title, i.level, m.matched_on, m.score "
        "FROM matches m JOIN clients c ON c.id = m.client_id "
        "JOIN items i ON i.id = m.item_id "
        "WHERE m.delivered_at IS NULL ORDER BY c.name, m.score DESC"
    ).fetchall()
    if not rows:
        print("  (none)")
    for r in rows:
        print(f"  [{r['client']}] ({r['level']}, {r['score']:.1f}) {(r['title'] or '')[:70]}")
        print(f"        {r['matched_on']}")

    conn.close()
    return 0


def main() -> int:
    # Item titles carry non-ASCII (Greek from Cyprus sources, zero-width spaces
    # from EBA). Force UTF-8 stdout so printing never crashes on a legacy console.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="Match reviewed items to clients.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="match reviewed/published items and write the match ledger")
    preview_parser = sub.add_parser(
        "preview", help="match every triaged item without writing (for testing)"
    )
    preview_parser.add_argument("--limit", type=int, help="show at most N candidate matches")
    sub.add_parser("report", help="show current matches and the undelivered queue")
    args = parser.parse_args()

    if args.command == "run":
        return run()
    if args.command == "preview":
        return run(preview=True, limit=args.limit)
    return report()


if __name__ == "__main__":
    sys.exit(main())
