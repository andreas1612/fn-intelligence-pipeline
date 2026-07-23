"""SQLite store: items, triage columns, per-source high-water mark, department routes.

Idempotency (the "run many times without duplicate work" requirement):
  - items.content_hash is UNIQUE; insert is INSERT OR IGNORE, so re-collecting a
    feed inserts nothing already seen.
  - sync_state records each source's last run + newest item date (high-water mark).
  - triage only ever processes rows where triaged_at IS NULL, so re-running never
    re-spends on an already-tagged item.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone

from . import config


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(title: str, url: str) -> str:
    norm = re.sub(r"\s+", " ", (title or "").strip().lower()) + "|" + (url or "").strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    source_category TEXT NOT NULL,
    title           TEXT NOT NULL,
    url             TEXT NOT NULL,
    published_at    TEXT,
    retrieved_at    TEXT NOT NULL,
    summary         TEXT,
    content_hash    TEXT NOT NULL UNIQUE,
    -- triage (null until triaged) --
    triaged_at      TEXT,
    theme_tags      TEXT,      -- JSON array
    jurisdiction    TEXT,
    doc_type        TEXT,
    level           TEXT,      -- Urgent|High|Standard|Low
    confidence      TEXT,      -- high|medium|low
    ai_summary      TEXT,
    fetch_status    TEXT,      -- ok | fetch_error:* | empty_content | non_html:*
    archived        INTEGER NOT NULL DEFAULT 0,  -- 1 = low-confidence/other, not routed
    model           TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER
);

CREATE TABLE IF NOT EXISTS sync_state (
    source            TEXT PRIMARY KEY,
    last_run_at       TEXT,
    last_published_at TEXT,     -- high-water mark: newest item seen so far
    last_run_new      INTEGER,
    last_run_seen     INTEGER
);

CREATE TABLE IF NOT EXISTS routes (
    item_id       INTEGER NOT NULL,
    department    TEXT NOT NULL,
    subdepartment TEXT NOT NULL DEFAULT '',
    matched_on    TEXT,
    score         REAL,
    created_at    TEXT,
    PRIMARY KEY (item_id, department, subdepartment)
);

CREATE INDEX IF NOT EXISTS idx_items_triaged ON items(triaged_at);
CREATE INDEX IF NOT EXISTS idx_routes_dept ON routes(department, subdepartment);
"""


def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == col for r in rows)


def migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for existing databases (never drop/alter data)."""
    if not _column_exists(conn, "items", "fetch_status"):
        conn.execute("ALTER TABLE items ADD COLUMN fetch_status TEXT")
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    migrate(conn)
    conn.commit()


def insert_item(conn: sqlite3.Connection, item: dict) -> bool:
    """INSERT OR IGNORE by content_hash. Returns True if a new row was inserted.
    Non-English/Greek items are dropped at the door (language gate)."""
    from .lang import is_allowed
    if not is_allowed(item.get("title", ""), item.get("summary", "")):
        return False
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO items
            (source, source_category, title, url, published_at, retrieved_at,
             summary, content_hash)
        VALUES (:source, :source_category, :title, :url, :published_at,
                :retrieved_at, :summary, :content_hash)
        """,
        item,
    )
    return cur.rowcount > 0


def update_sync_state(conn: sqlite3.Connection, source: str, new_count: int,
                      seen_count: int, newest_published: str | None) -> None:
    row = conn.execute(
        "SELECT last_published_at FROM sync_state WHERE source = ?", (source,)
    ).fetchone()
    prev = row["last_published_at"] if row else None
    hwm = max(x for x in (prev, newest_published) if x) if (prev or newest_published) else None
    conn.execute(
        """
        INSERT INTO sync_state (source, last_run_at, last_published_at,
                                last_run_new, last_run_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(source) DO UPDATE SET
            last_run_at=excluded.last_run_at,
            last_published_at=excluded.last_published_at,
            last_run_new=excluded.last_run_new,
            last_run_seen=excluded.last_run_seen
        """,
        (source, utc_now_iso(), hwm, new_count, seen_count),
    )
    conn.commit()


def fetch_untriaged(conn: sqlite3.Connection, limit: int | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM items WHERE triaged_at IS NULL ORDER BY id"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def counts(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) c FROM items").fetchone()["c"]
    triaged = conn.execute(
        "SELECT COUNT(*) c FROM items WHERE triaged_at IS NOT NULL"
    ).fetchone()["c"]
    routed = conn.execute("SELECT COUNT(DISTINCT item_id) c FROM routes").fetchone()["c"]
    return {"items": total, "triaged": triaged, "routed": routed}
