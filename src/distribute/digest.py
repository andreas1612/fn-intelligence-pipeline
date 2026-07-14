"""Per-client digest from the match ledger (D-024).

Builds one Markdown digest per client from that client's undelivered matches,
grouped by level, showing the summary triage already wrote and the reason the
item matched. Fully deterministic.

No model calls. The digest reuses items.ai_summary from triage. Summaries derive
strictly from fetched text (hard rule 2), and an LLM-written executive summary
would be a new claim about the items that no human reviewed. That is a separate
decision, not this module's to take.

The human gate is re-asserted here. Matching already restricts itself to items
with review_status in ('Reviewed', 'Published'), so this is deliberately
redundant: a match row is written once and read later, and an item can be moved
back to New or Discarded on the Notion board in between. The gate is the product
promise, so it is checked at the point of sending, not only at the point of
matching.

delivered_at is the idempotency key. It is written only after a channel reports
success, so a delivered match is never re-sent and a failed send is retried on
the next run.

Run with:
    python -m src.distribute.digest --client "<name>"     # preview, writes nothing
    python -m src.distribute.digest --all                 # preview every client
    python -m src.distribute.digest --all --send          # deliver and mark
    python -m src.distribute.digest --all --send --channel console
"""

import argparse
import sqlite3
import sys
from datetime import date, datetime, timezone

from src import clients as clients_module
from src import db, matching, migrate
from src.collectors.base import logger
from src.distribute import channels
from src.triage import LEVELS

# Only these two review states may ever be sent (D-018). Matching enforces this
# and so does the query below.
SENDABLE = ("Reviewed", "Published")

# One placeholder per sendable status, so the gate stays parameterised (no f-string
# interpolation into SQL) and cannot drift from SENDABLE.
_STATUS_PLACEHOLDERS = ", ".join("?" for _ in SENDABLE)

UNDELIVERED_SQL = f"""
SELECT m.item_id, m.score, m.matched_on,
       i.title, i.url, i.source, i.level, i.ai_summary, i.published_at,
       i.flagged, i.flag_reason
FROM matches m
JOIN items i ON i.id = m.item_id
WHERE m.client_id = ?
  AND m.delivered_at IS NULL
  AND i.review_status IN ({_STATUS_PLACEHOLDERS})
  AND i.triaged_at IS NOT NULL
  AND i.auto_discard IS NULL
  AND i.level IS NOT NULL
ORDER BY m.score DESC, i.id
"""

MARK_DELIVERED_SQL = """
UPDATE matches SET delivered_at = ?
WHERE client_id = ? AND item_id = ? AND delivered_at IS NULL
"""

_LEVEL_RANK = {level: index for index, level in enumerate(LEVELS)}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Read -----------------------------------------------------------------


def active_clients(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT id, name FROM clients WHERE active = 1 ORDER BY name"))


def find_client(conn: sqlite3.Connection, name: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, name, active FROM clients WHERE name = ?", (name,)
    ).fetchone()
    if row is None:
        known = [r["name"] for r in conn.execute("SELECT name FROM clients ORDER BY name")]
        raise SystemExit(
            f"No client named {name!r}.\n"
            + ("Known clients: " + ", ".join(known) if known else
               "No clients seeded. Run: python -m src.clients seed")
        )
    if not row["active"]:
        logger.warning("client %r is inactive; it will not be sent to", name)
    return row


def undelivered(conn: sqlite3.Connection, client_id: int) -> list[sqlite3.Row]:
    return list(conn.execute(UNDELIVERED_SQL, (client_id, *SENDABLE)))


def group_by_level(rows: list[sqlite3.Row]) -> list[tuple[str, list[sqlite3.Row]]]:
    """Group rows into taxonomy level order, most urgent first. Empty levels are
    dropped, so a digest never shows a heading with nothing under it."""
    buckets: dict[str, list[sqlite3.Row]] = {level: [] for level in LEVELS}
    for row in rows:
        buckets.setdefault(row["level"], []).append(row)
    ordered = sorted(buckets.items(), key=lambda kv: _LEVEL_RANK.get(kv[0], 99))
    return [(level, items) for level, items in ordered if items]


# --- Render ---------------------------------------------------------------


def render_entry(row: sqlite3.Row) -> list[str]:
    summary = (row["ai_summary"] or "").strip() or "_No summary available for this item._"
    lines = [
        f"### {row['title'] or '(untitled)'}",
        "",
        f"**Source**: {row['source']}  ",
        f"**Published**: {row['published_at'] or 'not stated'}  ",
        f"**Link**: {row['url']}",
        "",
        summary,
        "",
        f"_Matched on {row['matched_on']}._",
    ]
    # A flagged item reached the client only because a human reviewed it and let
    # it through. Say why it was flagged rather than hiding it.
    if row["flagged"] and (row["flag_reason"] or "").strip():
        lines += ["", f"_Flagged at triage: {row['flag_reason'].strip()}_"]
    lines.append("")
    return lines


def render_digest(client_name: str, rows: list[sqlite3.Row], on_date: date) -> str:
    """Build the Markdown digest. Pure: no database, no clock, no I/O."""
    grouped = group_by_level(rows)
    count = len(rows)
    plural = "item" if count == 1 else "items"

    lines = [
        f"# Finalogic intelligence digest: {client_name}",
        "",
        f"{on_date.isoformat()} | {count} {plural} matched to your profile",
        "",
        "Every item below was published by a named regulatory or security source, "
        "classified against Finalogic's taxonomy, and reviewed by a person before "
        "being sent.",
        "",
    ]

    for level, items in grouped:
        lines += [f"## {level}", ""]
        for row in items:
            lines += render_entry(row)

    lines += [
        "---",
        "",
        "Finalogic Ltd. Sources are named against each item. "
        "Reply to this digest to change what you receive.",
        "",
    ]
    return "\n".join(lines)


# --- Write ----------------------------------------------------------------


def mark_delivered(conn: sqlite3.Connection, client_id: int, item_ids: list[int]) -> int:
    """Stamp delivered_at on the matches just sent. Called only after a channel
    reports success. The `delivered_at IS NULL` guard makes a re-run a no-op."""
    timestamp = now_iso()
    marked = 0
    for item_id in item_ids:
        cursor = conn.execute(MARK_DELIVERED_SQL, (timestamp, client_id, item_id))
        marked += cursor.rowcount
    conn.commit()
    return marked


# --- Run ------------------------------------------------------------------


def distribute_client(
    conn: sqlite3.Connection,
    client: sqlite3.Row,
    channel: channels.Channel | None,
    on_date: date,
    send: bool,
) -> dict:
    """Build one client's digest and, if sending, deliver it and mark it."""
    name = client["name"]
    rows = undelivered(conn, client["id"])

    if not rows:
        logger.info("client=%s nothing undelivered, skipped", name)
        return {"client": name, "items": 0, "sent": False, "destination": None}

    markdown = render_digest(name, rows, on_date)

    if not send:
        print(markdown)
        return {"client": name, "items": len(rows), "sent": False, "destination": None}

    assert channel is not None
    try:
        destination = channel.deliver(name, markdown, on_date)
    except channels.DeliveryError as exc:
        # Nothing is marked. delivered_at stays null and the next run retries.
        logger.error("client=%s delivery FAILED via %s: %s", name, channel.name, exc)
        return {"client": name, "items": len(rows), "sent": False,
                "destination": None, "error": str(exc)}

    marked = mark_delivered(conn, client["id"], [row["item_id"] for row in rows])
    logger.info(
        "client=%s delivered %d item(s) via %s to %s, marked %d",
        name, len(rows), channel.name, destination, marked,
    )
    return {"client": name, "items": len(rows), "sent": True, "destination": destination}


def run(
    client_name: str | None = None,
    all_clients: bool = False,
    send: bool = False,
    channel_name: str | None = None,
    on_date: date | None = None,
) -> int:
    on_date = on_date or datetime.now(timezone.utc).date()

    conn = db.connect()
    conn.row_factory = sqlite3.Row
    migrate.migrate(conn)
    clients_module.ensure_schema(conn)
    matching.ensure_schema(conn)

    if all_clients:
        targets = active_clients(conn)
        if not targets:
            logger.warning("no active clients; seed them with: python -m src.clients seed")
    else:
        assert client_name is not None
        targets = [find_client(conn, client_name)]

    channel = channels.build_channel(channel_name) if send else None
    if send and channel is not None:
        logger.info("delivering via the %s channel", channel.name)

    results = [distribute_client(conn, c, channel, on_date, send) for c in targets]
    conn.close()

    print_summary(results, send)
    return 1 if any(r.get("error") for r in results) else 0


def print_summary(results: list[dict], send: bool) -> None:
    print("\n--- Distribution summary ---")
    if not results:
        print("No clients.")
        return

    total = sum(r["items"] for r in results)
    for r in results:
        if r.get("error"):
            print(f"  {r['client']}: FAILED, {r['items']} item(s) left undelivered ({r['error']})")
        elif r["sent"]:
            print(f"  {r['client']}: sent {r['items']} item(s) to {r['destination']}")
        elif r["items"]:
            print(f"  {r['client']}: {r['items']} item(s) ready (preview only, nothing marked)")
        else:
            print(f"  {r['client']}: nothing undelivered")

    if not send and total:
        print("\nPreview only. Nothing was sent and nothing was marked delivered.")
        print("Add --send to deliver via the configured channel.")


def main() -> int:
    channels.force_utf8_stdout()

    parser = argparse.ArgumentParser(
        description="Build and deliver per-client digests from the match ledger."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--client", help="build the digest for one client, by name")
    target.add_argument("--all", action="store_true", help="every active client")
    parser.add_argument(
        "--send",
        action="store_true",
        help="deliver via the configured channel and set delivered_at. Without this, "
             "the digest is printed and nothing is written.",
    )
    parser.add_argument(
        "--channel",
        choices=sorted(channels.CHANNELS),
        help="override the channel in config/distribution.yaml",
    )
    args = parser.parse_args()

    return run(
        client_name=args.client,
        all_clients=args.all,
        send=args.send,
        channel_name=args.channel,
    )


if __name__ == "__main__":
    sys.exit(main())
