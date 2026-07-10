"""Phase 3 schema migration: triage columns and overrides table.

Idempotent. Safe to run twice. Adds columns only, never alters or drops
existing raw columns or rows (D-008, Phase 3 build spec section 1).

Run standalone with: python -m src.migrate
"""

import sqlite3
import sys

from src import db

# Columns added to items. Order is the spec order. Existing raw columns
# (id, source, title, url, published_at, retrieved_at, content_hash, summary)
# are never touched. ai_summary is separate from summary, which holds the
# feed snippet.
TRIAGE_COLUMNS: dict[str, str] = {
    "triaged_at": "TEXT",
    "auto_discard": "TEXT",
    "theme_tags": "TEXT",
    "sector_tags": "TEXT",
    "jurisdiction": "TEXT",
    "type": "TEXT",
    "level": "TEXT",
    "rules_applied": "TEXT",
    "ai_summary": "TEXT",
    "flagged": "INTEGER",
    "flag_rules": "TEXT",
    "flag_reason": "TEXT",
    "confidence": "TEXT",
    "fetch_status": "TEXT",
    "model": "TEXT",
    "input_tokens": "INTEGER",
    "output_tokens": "INTEGER",
    "review_status": "TEXT DEFAULT 'New'",
    "notion_page_id": "TEXT",
}

OVERRIDES_SCHEMA = """
CREATE TABLE IF NOT EXISTS overrides (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id        INTEGER NOT NULL,
    original_level TEXT NOT NULL,
    final_level    TEXT NOT NULL,
    reason         TEXT,
    recorded_at    TEXT NOT NULL
);
"""


def existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply the Phase 3 migration. Returns the list of columns added."""
    present = existing_columns(conn, "items")
    added = []
    for column, declaration in TRIAGE_COLUMNS.items():
        if column not in present:
            conn.execute(f"ALTER TABLE items ADD COLUMN {column} {declaration}")
            added.append(column)
    conn.execute(OVERRIDES_SCHEMA)
    conn.commit()
    return added


def main() -> int:
    conn = db.connect()
    before = conn.execute("SELECT count(*) FROM items").fetchone()[0]
    added = migrate(conn)
    after = conn.execute("SELECT count(*) FROM items").fetchone()[0]
    conn.close()

    if added:
        print(f"Added {len(added)} columns to items: {', '.join(added)}")
    else:
        print("No columns added, schema already current")
    print("Table overrides present")
    print(f"Rows in items: {before} before, {after} after")
    return 0


if __name__ == "__main__":
    sys.exit(main())
