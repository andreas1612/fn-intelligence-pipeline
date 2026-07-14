"""Shared test fixtures.

Every test runs against a temporary SQLite database built by the real schema and
migration code, never against the committed finalogic.db. The modules under test
take a connection, so the seam is the connection itself: no monkeypatching, and
no test can touch the system of record.
"""

import json
import sqlite3

import pytest

from src import clients as clients_module
from src import db, matching, migrate

# A triaged, human-reviewed, EU-wide DORA item. The shape of a real row.
BASE_ITEM = {
    "source": "ESMA",
    "title": "ESMA consults on ICT incident reporting under DORA",
    "url": "https://www.esma.europa.eu/example",
    "published_at": "2026-07-01",
    "retrieved_at": "2026-07-02T06:00:00+00:00",
    "summary": "feed snippet",
    "triaged_at": "2026-07-03T06:00:00+00:00",
    "auto_discard": None,
    "theme_tags": ["DORA", "ICT incident reporting"],
    "sector_tags": ["Investment firms"],
    "jurisdiction": "EU",
    "type": "Consultation",
    "level": "High",
    "rules_applied": ["H-2"],
    "ai_summary": "ESMA opened a consultation on incident reporting.",
    "flagged": 0,
    "flag_rules": [],
    "flag_reason": "",
    "confidence": "high",
    "review_status": "Reviewed",
}


@pytest.fixture
def conn(tmp_path):
    """A temporary database with the full schema applied."""
    connection = db.connect(tmp_path / "test.db")
    connection.row_factory = sqlite3.Row
    migrate.migrate(connection)
    clients_module.ensure_schema(connection)
    matching.ensure_schema(connection)
    yield connection
    connection.close()


def add_item(conn: sqlite3.Connection, **overrides) -> int:
    """Insert one triaged item. Overrides replace any BASE_ITEM field."""
    item = {**BASE_ITEM, **overrides}
    for key in ("theme_tags", "sector_tags", "rules_applied", "flag_rules"):
        item[key] = json.dumps(item[key])
    item["content_hash"] = db.content_hash(item["title"], item["url"])

    columns = ", ".join(item)
    placeholders = ", ".join("?" for _ in item)
    cursor = conn.execute(
        f"INSERT INTO items ({columns}) VALUES ({placeholders})", tuple(item.values())
    )
    conn.commit()
    return cursor.lastrowid


def add_client(
    conn: sqlite3.Connection,
    name: str = "Test Client",
    min_level: str = "Standard",
    sectors=(),
    jurisdictions=("EU",),
    themes=(),
    active: int = 1,
) -> int:
    cursor = conn.execute(
        "INSERT INTO clients (name, active, min_level) VALUES (?, ?, ?)",
        (name, active, min_level),
    )
    client_id = cursor.lastrowid
    for table, column, values in (
        ("client_sectors", "sector_tag", sectors),
        ("client_jurisdictions", "jurisdiction_tag", jurisdictions),
        ("client_themes", "theme_tag", themes),
    ):
        for value in values:
            conn.execute(
                f"INSERT INTO {table} (client_id, {column}) VALUES (?, ?)",
                (client_id, value),
            )
    conn.commit()
    return client_id
