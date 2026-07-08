"""SQLite system of record. Single items table, per D-008."""

import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "finalogic.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source        TEXT NOT NULL,
    title         TEXT NOT NULL,
    url           TEXT NOT NULL,
    published_at  TEXT,
    retrieved_at  TEXT NOT NULL,
    content_hash  TEXT NOT NULL UNIQUE,
    summary       TEXT
);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def content_hash(title: str, url: str) -> str:
    normalised = f"{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def insert_item(conn: sqlite3.Connection, item: dict) -> bool:
    """Insert one item. Returns True if newly inserted, False if a duplicate."""
    hash_value = content_hash(item["title"], item["url"])
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO items
            (source, title, url, published_at, retrieved_at, content_hash, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["source"],
            item["title"],
            item["url"],
            item.get("published_at"),
            item["retrieved_at"],
            hash_value,
            item.get("summary"),
        ),
    )
    conn.commit()
    return cursor.rowcount > 0
