"""Read-only inspector for finalogic.db.

The database is a binary SQLite file. It cannot be opened with cat, type, or
start. Use this to look inside it from the command line.

Run with (from the project root):
    python -m src.inspect_db overview          # tables, row counts, key breakdowns
    python -m src.inspect_db items --limit 10  # most recent items
    python -m src.inspect_db triaged           # items that have been triaged
    python -m src.inspect_db matches           # client matches and their reasons
    python -m src.inspect_db sql "SELECT ..."  # any read-only query

Nothing here writes. SELECT statements only.
"""

import argparse
import sqlite3
import sys

from src import db


def _connect() -> sqlite3.Connection:
    conn = db.connect()
    conn.row_factory = sqlite3.Row
    return conn


def _print_rows(rows) -> None:
    if not rows:
        print("(no rows)")
        return
    headers = rows[0].keys()
    widths = {h: max(len(h), *(len(str(r[h])[:40]) for r in rows)) for h in headers}
    print(" | ".join(h.ljust(widths[h]) for h in headers))
    print("-+-".join("-" * widths[h] for h in headers))
    for row in rows:
        print(" | ".join(str(row[h])[:40].ljust(widths[h]) for h in headers))
    print(f"\n{len(rows)} row(s).")


def overview(conn: sqlite3.Connection) -> None:
    print("=== Tables ===")
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    for table in tables:
        count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  {table:<22} {count:>6} row(s)")

    print("\n=== Items by source ===")
    _print_rows(conn.execute(
        "SELECT source, count(*) AS items FROM items GROUP BY source ORDER BY items DESC"
    ).fetchall())

    print("\n=== Triage status ===")
    _print_rows(conn.execute(
        "SELECT "
        "  sum(CASE WHEN triaged_at IS NULL THEN 1 ELSE 0 END) AS untriaged, "
        "  sum(CASE WHEN triaged_at IS NOT NULL THEN 1 ELSE 0 END) AS triaged, "
        "  sum(CASE WHEN flagged = 1 THEN 1 ELSE 0 END) AS flagged "
        "FROM items"
    ).fetchall())

    print("\n=== Level and review status (triaged only) ===")
    _print_rows(conn.execute(
        "SELECT level, review_status, count(*) AS items FROM items "
        "WHERE triaged_at IS NOT NULL GROUP BY level, review_status ORDER BY items DESC"
    ).fetchall())


def items(conn: sqlite3.Connection, limit: int) -> None:
    _print_rows(conn.execute(
        "SELECT id, source, substr(title, 1, 60) AS title, published_at "
        "FROM items ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall())


def triaged(conn: sqlite3.Connection, limit: int) -> None:
    _print_rows(conn.execute(
        "SELECT id, source, level, jurisdiction, review_status, "
        "substr(title, 1, 45) AS title "
        "FROM items WHERE triaged_at IS NOT NULL ORDER BY id LIMIT ?", (limit,)
    ).fetchall())


def matches(conn: sqlite3.Connection, limit: int) -> None:
    _print_rows(conn.execute(
        "SELECT c.name AS client, m.item_id, i.level, m.score, "
        "substr(i.title, 1, 35) AS title, substr(m.matched_on, 1, 40) AS matched_on, "
        "CASE WHEN m.delivered_at IS NULL THEN 'no' ELSE 'yes' END AS delivered "
        "FROM matches m "
        "JOIN clients c ON c.id = m.client_id "
        "JOIN items i ON i.id = m.item_id "
        "ORDER BY c.name, m.score DESC LIMIT ?", (limit,)
    ).fetchall())


def run_sql(conn: sqlite3.Connection, statement: str) -> int:
    if not statement.strip().lower().startswith("select"):
        print("Only SELECT statements are allowed here. This inspector is read-only.")
        return 1
    _print_rows(conn.execute(statement).fetchall())
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="Read-only inspector for finalogic.db")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("overview", help="tables, row counts, source and triage breakdowns")
    for name, help_text in [
        ("items", "most recent collected items"),
        ("triaged", "items that have been triaged"),
        ("matches", "client matches and why they matched"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--limit", type=int, default=20)
    sql_parser = sub.add_parser("sql", help="run any read-only SELECT query")
    sql_parser.add_argument("statement", help="the SELECT statement to run")

    args = parser.parse_args()
    conn = _connect()

    if args.command == "overview":
        overview(conn)
    elif args.command == "items":
        items(conn, args.limit)
    elif args.command == "triaged":
        triaged(conn, args.limit)
    elif args.command == "matches":
        matches(conn, args.limit)
    else:
        code = run_sql(conn, args.statement)
        conn.close()
        return code

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
