"""Notion review board sync (D-018).

push: one page per triaged item not yet in Notion.
pull: read Status, Level, Override reason back; log level overrides.

SQLite stays the system of record (D-008). Sync-back writes only
items.review_status and rows in overrides. Raw and triage columns are
never modified here.

Run with:
    python -m src.notion_sync create --parent-page-id <id>
    python -m src.notion_sync push
    python -m src.notion_sync pull
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError

from src import db, migrate
from src.collectors.base import logger
from src.sources import SOURCES as FEED_SOURCES
from src.triage import LEVELS, TAXONOMY_PATH, load_taxonomy

# The Notion API allows roughly 3 requests per second. Volume is tiny.
RATE_LIMIT_SLEEP = 0.35

# Notion rejects a rich_text or title value longer than 2000 characters.
TEXT_CAP = 2000

STATUSES = ("New", "Reviewed", "Published", "Discarded")
CONFIDENCE = ("high", "medium", "low")
# Derived from the verified feed register, not a second copy of it: a source added
# in src/sources.py must not need a matching edit here to appear on the board.
SOURCES = tuple(FEED_SOURCES)

# Placeholder used when a level is absent on either side of an override.
# overrides.original_level and overrides.final_level are NOT NULL, but a
# discarded or invalid item carries no AI level.
NO_LEVEL = "(none)"

PUSH_SQL = """
SELECT id, source, title, url, published_at, theme_tags, sector_tags,
       jurisdiction, type, level, ai_summary, flagged, flag_reason, confidence
FROM items
WHERE triaged_at IS NOT NULL AND notion_page_id IS NULL
ORDER BY id
"""

PULL_SQL = (
    "SELECT id, level, notion_page_id FROM items WHERE notion_page_id IS NOT NULL ORDER BY id"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_list(value: str | None) -> list[str]:
    """Decode a JSON array column. Invalid-output items have null tag columns."""
    if not value:
        return []
    decoded = json.loads(value)
    return decoded if isinstance(decoded, list) else []


def options(names) -> dict:
    return {"options": [{"name": n} for n in names]}


def build_schema() -> dict:
    """Property schema per D-018.

    Select and multi-select options are generated from the locked taxonomy at
    runtime, so the board can never drift from taxonomy-v1.0.md.
    """
    taxonomy = load_taxonomy(TAXONOMY_PATH.read_text(encoding="utf-8"))
    return {
        "Title": {"title": {}},
        "URL": {"url": {}},
        "Source": {"select": options(SOURCES)},
        "Published date": {"date": {}},
        "Level": {"select": options(LEVELS)},
        "AI Level": {"select": options(LEVELS)},
        "Themes": {"multi_select": options(sorted(taxonomy.themes))},
        "Sectors": {"multi_select": options(sorted(taxonomy.sectors))},
        "Jurisdiction": {"select": options(sorted(taxonomy.jurisdictions))},
        "Type": {"select": options(sorted(taxonomy.types))},
        "Status": {"select": options(STATUSES)},
        "Flagged": {"checkbox": {}},
        "Flag reason": {"rich_text": {}},
        "Summary": {"rich_text": {}},
        "Confidence": {"select": options(CONFIDENCE)},
        "Override reason": {"rich_text": {}},
        "item_id": {"number": {}},
    }


# --- Property value builders and readers -----------------------------------


def text_value(value: str | None) -> dict:
    if not value:
        return {"rich_text": []}
    return {"rich_text": [{"text": {"content": value[:TEXT_CAP]}}]}


def select_value(value: str | None) -> dict:
    return {"select": {"name": value} if value else None}


def read_select(props: dict, name: str) -> str | None:
    prop = props.get(name) or {}
    selected = prop.get("select")
    return selected.get("name") if selected else None


def read_text(props: dict, name: str) -> str:
    prop = props.get(name) or {}
    return "".join(part.get("plain_text", "") for part in prop.get("rich_text", [])).strip()


def page_properties(row: sqlite3.Row) -> dict:
    level = row["level"]
    return {
        "Title": {"title": [{"text": {"content": (row["title"] or "(untitled)")[:TEXT_CAP]}}]},
        "URL": {"url": row["url"] or None},
        "Source": select_value(row["source"]),
        "Published date": {"date": {"start": row["published_at"]} if row["published_at"] else None},
        # Level is the working value reviewers may change. AI Level is written
        # once here and never written again (D-018).
        "Level": select_value(level),
        "AI Level": select_value(level),
        "Themes": {"multi_select": [{"name": t} for t in json_list(row["theme_tags"])]},
        "Sectors": {"multi_select": [{"name": s} for s in json_list(row["sector_tags"])]},
        "Jurisdiction": select_value(row["jurisdiction"]),
        "Type": select_value(row["type"]),
        "Status": select_value("New"),
        "Flagged": {"checkbox": bool(row["flagged"])},
        "Flag reason": text_value(row["flag_reason"]),
        "Summary": text_value(row["ai_summary"]),
        "Confidence": select_value(row["confidence"]),
        "Override reason": {"rich_text": []},
        "item_id": {"number": row["id"]},
    }


# --- Client helpers --------------------------------------------------------


def notion_client() -> Client:
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        raise SystemExit("NOTION_API_KEY is not set. Copy .env.example to .env and fill it in.")
    return Client(auth=token)


def resolve_data_source_id(client: Client, database_id: str) -> str:
    """Notion API 2025-09-03 parents pages to a data source, not a database.

    NOTION_DATABASE_ID stays the owner-facing database ID; the data source is
    resolved here so the operator never has to know about it.
    """
    database = client.databases.retrieve(database_id=database_id)
    sources = database.get("data_sources") or []
    if not sources:
        raise SystemExit(f"Notion database {database_id} exposes no data source.")
    return sources[0]["id"]


def require_database_id() -> str:
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        raise SystemExit(
            "NOTION_DATABASE_ID is not set, so there is no review board to sync to.\n"
            "\n"
            "This script will not create a database silently: the parent page is\n"
            "yours to choose. To create the board:\n"
            "\n"
            "  1. In Notion, create or pick a page to hold the board.\n"
            "  2. Share that page with your integration (Share, then invite it).\n"
            "  3. Copy the page ID from its URL (the 32-character hex string).\n"
            "  4. Run: python -m src.notion_sync create --parent-page-id <id>\n"
            "  5. Put the database ID it prints into .env as NOTION_DATABASE_ID.\n"
        )
    return database_id


# --- Commands --------------------------------------------------------------


def create(parent_page_id: str) -> int:
    client = notion_client()
    database = client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Finalogic intelligence review"}}],
        initial_data_source={"properties": build_schema()},
    )
    print(f"Created database: {database['id']}")
    print("\nAdd this line to .env:\n")
    print(f"NOTION_DATABASE_ID={database['id']}")
    return 0


def push() -> int:
    load_dotenv()
    database_id = require_database_id()
    client = notion_client()
    data_source_id = resolve_data_source_id(client, database_id)

    conn = db.connect()
    conn.row_factory = sqlite3.Row
    migrate.migrate(conn)

    rows = list(conn.execute(PUSH_SQL))
    logger.info("pushing %d items to Notion", len(rows))

    pushed = failed = 0
    for row in rows:
        time.sleep(RATE_LIMIT_SLEEP)
        try:
            page = client.pages.create(
                parent={"type": "data_source_id", "data_source_id": data_source_id},
                properties=page_properties(row),
            )
        except APIResponseError as exc:
            failed += 1
            logger.error("item=%d Notion push failed: %s", row["id"], exc)
            continue

        conn.execute("UPDATE items SET notion_page_id = ? WHERE id = ?", (page["id"], row["id"]))
        conn.commit()
        pushed += 1
        logger.info("item=%d pushed page=%s", row["id"], page["id"])

    conn.close()
    print(f"\nPushed {pushed} items, {failed} failed.")
    return 1 if failed else 0


def pull() -> int:
    load_dotenv()
    require_database_id()
    client = notion_client()

    conn = db.connect()
    conn.row_factory = sqlite3.Row
    migrate.migrate(conn)

    rows = list(conn.execute(PULL_SQL))
    logger.info("reading %d Notion pages", len(rows))

    statuses = overrides = failed = 0
    missing_reason: list[int] = []
    edited_ai_level: list[tuple[int, str, str]] = []

    for row in rows:
        item_id = row["id"]
        time.sleep(RATE_LIMIT_SLEEP)
        try:
            page = client.pages.retrieve(page_id=row["notion_page_id"])
        except APIResponseError as exc:
            failed += 1
            logger.error("item=%d Notion read failed: %s", item_id, exc)
            continue

        props = page.get("properties", {})
        status = read_select(props, "Status")
        level = read_select(props, "Level")
        ai_level = read_select(props, "AI Level")
        reason = read_text(props, "Override reason")

        if status:
            conn.execute("UPDATE items SET review_status = ? WHERE id = ?", (status, item_id))
            statuses += 1

        # The original level comes from SQLite, never from the board (D-022).
        # Notion's AI Level is a display copy; SQLite is the system of record
        # (D-008). Reading the copy lets a mis-edit of the write-once column
        # forge an override row.
        original = row["level"] or NO_LEVEL
        final = level or NO_LEVEL
        board_original = ai_level or NO_LEVEL

        if board_original != original:
            # AI Level is written once and never edited (D-018), so a mismatch
            # is a mis-edit, not an override. Refuse to log; warn instead.
            edited_ai_level.append((item_id, original, board_original))
            logger.warning(
                "item=%d AI Level edited on the board: expected %s, found %s. Override not logged.",
                item_id, original, board_original,
            )
            conn.commit()
            continue

        if final != original:
            existing = conn.execute(
                "SELECT 1 FROM overrides WHERE item_id = ? AND final_level = ?",
                (item_id, final),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO overrides (item_id, original_level, final_level, reason,"
                    " recorded_at) VALUES (?, ?, ?, ?, ?)",
                    (item_id, original, final, reason or None, now_iso()),
                )
                overrides += 1
                if not reason:
                    missing_reason.append(item_id)
                logger.info("item=%d override %s -> %s", item_id, original, final)

        conn.commit()

    conn.close()

    print(f"\nStatuses updated: {statuses}")
    print(f"Overrides logged: {overrides}")
    if failed:
        print(f"Pages that could not be read: {failed}")
    if missing_reason:
        print("\nWARNING: overrides logged with no reason given, for items:")
        print("  " + ", ".join(str(i) for i in missing_reason))
        print("  Add an Override reason in Notion so the Phase 5 tuning has context.")
    if edited_ai_level:
        print("\nWARNING: AI Level was edited on the board. It is written once and")
        print("never edited (D-018), so no override was logged for these items:")
        for item_id, expected, found in edited_ai_level:
            print(f"  item {item_id}: expected {expected}, board shows {found}")
        print("  Restore AI Level to the expected value in Notion, then pull again.")
        print("  To change an item's level, edit Level, not AI Level.")
    return 1 if (failed or edited_ai_level) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync triaged items to and from Notion.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("push", help="create a Notion page for each newly triaged item")
    sub.add_parser("pull", help="read Status and Level back, log overrides")
    creator = sub.add_parser("create", help="create the review database under a parent page")
    creator.add_argument("--parent-page-id", required=True, help="Notion page ID to hold the board")

    args = parser.parse_args()
    load_dotenv()
    if args.command == "create":
        return create(args.parent_page_id)
    if args.command == "push":
        return push()
    return pull()


if __name__ == "__main__":
    sys.exit(main())
