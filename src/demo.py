"""One-command live demo of the full cycle.

    python -m src.demo              # 3 items
    python -m src.demo --limit 5

Runs collect, triage, review, match, and distribute end to end and narrates each
stage. Uses the real modules throughout: the real collectors against the real
source websites, the real prompt, the real locked taxonomy and scoring criteria,
the real validator, the real matching engine, the real digest.

Two things are different from a production run, and both are stated on screen:

  1. It works on a COPY of finalogic.db. The system of record is never written to.
  2. It stands in for the Notion reviewer by approving one item directly, because
     a demo cannot wait for a human. Everything else about the gate is real: you
     will see matching return nothing until that approval happens.

Costs a few cents: triage calls the model once per item.
"""

import argparse
import shutil
import sqlite3
import sys
import tempfile
import textwrap
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src import clients as clients_module
from src import db, matching, migrate, run as collect_run, triage
from src.distribute import channels, digest


# The date the demo presents itself as running on. Fixed, not today's date, so
# the demo log and the digest are reproducible: the same run twice produces the
# same output. Override with --date.
DEMO_DATE = date(2026, 7, 14)


def rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# Every column triage writes. Rewinding means clearing exactly these and nothing
# else: the raw collection columns (source, title, url, retrieved_at,
# content_hash) are never touched, so the item stays the real article it was.
TRIAGE_COLUMNS = (
    "triaged_at", "auto_discard", "theme_tags", "sector_tags", "jurisdiction",
    "type", "level", "rules_applied", "ai_summary", "flagged", "flag_rules",
    "flag_reason", "confidence", "fetch_status", "model", "input_tokens",
    "output_tokens", "notion_page_id",
)

# Real regulatory and security publications. KEV is excluded from the rewind pool
# because its 1,600-item catalogue would dominate the selection, and a demo built
# on CVE rows shows the pipeline routing vulnerabilities but not regulation.
DEMO_SOURCES = ("EBA", "ESMA", "CERT-EU")

REWIND_CANDIDATES = f"""
SELECT id FROM items
WHERE source IN ({','.join('?' * len(DEMO_SOURCES))})
ORDER BY COALESCE(published_at, retrieved_at) DESC, id DESC
LIMIT ?
"""


def rewind(conn: sqlite3.Connection, limit: int) -> list[int]:
    """Un-triage the most recent real items, on the COPY only.

    The demo would otherwise consume the untriaged backlog and have nothing left
    to show. Rewinding puts the newest genuine publications back into the queue so
    the full cycle can be demonstrated repeatedly, against real articles, with
    real model calls. The system of record is not open for writing here.
    """
    ids = [r["id"] for r in conn.execute(REWIND_CANDIDATES, (*DEMO_SOURCES, limit))]
    if not ids:
        return []

    placeholders = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE items SET {', '.join(f'{c} = NULL' for c in TRIAGE_COLUMNS)}, "
        f"review_status = 'New' WHERE id IN ({placeholders})",
        ids,
    )
    # Their match rows would otherwise survive as orphans pointing at items that
    # are, on this copy, no longer triaged.
    conn.execute(f"DELETE FROM matches WHERE item_id IN ({placeholders})", ids)
    conn.commit()
    return ids


def demo(limit: int, collect: bool, rewind_first: bool, on_date: date) -> int:
    channels.force_utf8_stdout()
    load_dotenv()  # KIE_API_KEY for triage

    # The demo triages against a COPY of the database, so its items are never
    # marked triaged in the system of record and it re-triages the same ones on
    # every run. Its output must therefore not be appended to the real audit log,
    # or repeated demo runs would fill it with duplicates of work that, as far as
    # the database is concerned, never happened.
    triage.ITEM_LOG_PATH = triage.ROOT / "logs" / "demo_items.jsonl"

    # Truncated, never appended. The demo re-triages the same items on every run,
    # so appending would pile up duplicate records of work that, as far as the
    # system of record is concerned, never happened. The file holds the latest
    # demo and nothing else.
    triage.ITEM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    triage.ITEM_LOG_PATH.write_text("", encoding="utf-8")

    # Fixed timestamp, not the live clock, so two runs of the same demo produce
    # identical log output and nothing in it can be mistaken for a real record.
    triage.ITEM_LOG_TIMESTAMP = f"{on_date.isoformat()}T09:00:00+00:00"

    rule("FINALOGIC INTELLIGENCE PIPELINE: live end-to-end demo")
    demo_db = Path(tempfile.gettempdir()) / "finalogic_demo.db"

    # --- collect (against the real websites, writing to the real database, as
    # the daily Action does) ---
    if collect:
        rule("STAGE 1  COLLECT  (live, against the real source websites)")
        print("Fetching EBA, ESMA, CERT-EU and CISA KEV now.")
        print("Items are deduplicated on a SHA-256 of the normalised title and URL,")
        print("so re-fetching the same catalogue day after day stores nothing new.\n")
        collect_run.run()

    shutil.copy(db.DB_PATH, demo_db)
    print(f"\nWorking on a COPY: {demo_db}")
    print("finalogic.db, the system of record, is not written to from here on.")

    conn = sqlite3.connect(demo_db)
    conn.row_factory = sqlite3.Row
    migrate.migrate(conn)
    clients_module.ensure_schema(conn)
    matching.ensure_schema(conn)

    # --- rewind, so the demo always has real, current items to work on ---
    if rewind_first:
        rewound = rewind(conn, limit)
        if rewound:
            print(f"\nRewound {len(rewound)} item(s) on the copy: the most recent real")
            print("publications from EBA, ESMA and CERT-EU are put back into the triage")
            print("queue so the full cycle can run. The articles are genuine and the model")
            print("calls below are live. Only the copy's triage state was reset.")

    # --- triage ---
    template = triage.load_prompt_template()
    taxonomy_text = triage.TAXONOMY_PATH.read_text(encoding="utf-8")
    scoring_text = triage.SCORING_PATH.read_text(encoding="utf-8")
    taxonomy = triage.load_taxonomy(taxonomy_text)

    items = list(conn.execute(triage.ELIGIBLE_SQL))[:limit]
    if not items:
        print("\nNothing to triage. Run without --no-rewind to reset the copy's triage")
        print("state and demonstrate the cycle on the most recent real items.")
        conn.close()
        return 0

    rule(f"STAGE 2  TRIAGE  ({len(items)} untriaged item(s), one model call each)")
    print("Each item is tagged against the LOCKED taxonomy and scored against the")
    print("LOCKED criteria, both injected into the prompt at runtime. The output is")
    print("validated before it is allowed into the database: a tag or level the")
    print("documents do not define is a hard failure, not a warning.\n")

    report = triage.RunReport(run_at=datetime.now(timezone.utc).isoformat(),
                              run_type="proof", items_eligible=len(items))

    triaged = []
    for item in items:
        read = triage.triage_item(conn, item, template, taxonomy, taxonomy_text,
                                  scoring_text, report, dry_run=False)
        if read is None:
            print(f"\n  item {item['id']}: left untriaged. Nothing written. A later run retries it.")
            continue
        triaged.append(item["id"])
        result = read["result"]

        print("\n" + "-" * 78)
        print(f"  ITEM {item['id']}   {item['source']}   "
              f"published {item['published_at'] or 'not stated'}")
        print(f"\n  {item['title']}")

        print("\n  1. WHAT IT READ  (the article, not the title)")
        print(f"     source document   {item['url']}")
        if read["fetch_status"] == "ok":
            capped = f", capped at {triage.FETCH_CHAR_CAP:,}" if read["truncated"] else ""
            print(f"     fetched live      {read['fetched_chars']:,} characters of page text{capped}")
            print(f"     feed snippet      {read['feed_snippet_chars']:,} characters")
            print(f"     prompt sent       {read['prompt_chars']:,} characters "
                  f"(page text + title + snippet + the two locked documents)")
            print(f"\n     First 400 characters of what the model actually saw:")
            for line in textwrap.wrap(read["excerpt"], 68):
                print(f"       {line}")
        else:
            print(f"     FETCH FAILED      {read['fetch_status']}")
            print("     The model saw the title and the feed snippet only, and F-3 is")
            print("     flagged so a reviewer knows the read was thin. Never silently skipped.")

        print("\n  2. WHAT IT DECIDED  (every level justified by a named rule)")
        print(f"     level             {result['level']}   "
              f"justified by {', '.join(result['rules_applied'])}")
        print(f"     themes            {', '.join(result['theme_tags'])}")
        print(f"     sectors           {', '.join(result['sector_tags']) or '(cross-sector)'}")
        print(f"     jurisdiction      {result['jurisdiction']}")
        print(f"     type              {result['type']}")
        print(f"     confidence        {result['confidence']}")
        if result["flagged"]:
            print(f"     FLAGGED           {', '.join(result['flag_rules'])}")
            for line in textwrap.wrap(result["flag_reason"], 62):
                print(f"       {line}")
            print("       -> A human must look at this before it can reach anyone.")
        else:
            print("     flagged           no")

        print("\n  3. THE SUMMARY  (from the page above only, no outside knowledge)")
        for line in textwrap.wrap(result["summary"], 68):
            print(f"     {line}")

        print(f"\n  4. WHAT IT COST")
        print(f"     {read['input_tokens']:,} in / {read['output_tokens']:,} out tokens"
              f"   =  ${read['cost_usd']:.5f}"
              f"   ({read['attempts']} model call, validated first time)"
              if read["attempts"] == 1 else
              f"     {read['input_tokens']:,} in / {read['output_tokens']:,} out tokens"
              f"   =  ${read['cost_usd']:.5f}   ({read['attempts']} calls: "
              f"first output failed validation and was retried)")

    print("\n" + "=" * 78)
    print(f"  RUN TOTAL: {report.items_triaged} triaged, {report.items_flagged} flagged, "
          f"{report.items_invalid} rejected by the validator")
    print(f"  {report.input_tokens:,} in / {report.output_tokens:,} out tokens on "
          f"{report.model}  =  ${report.cost_usd:.4f}")
    if report.items_triaged:
        per = report.cost_usd / report.items_triaged
        print(f"  ${per:.5f} per item  ->  about ${per * 6 * 365:.2f} a year at 6 items a day")
    print(f"\n  Full detail, one line per item with its source URL, appended to")
    print(f"  logs/{triage.ITEM_LOG_PATH.name}")

    # --- the gate ---
    rule("STAGE 3  HUMAN REVIEW  (the gate)")
    print("Triaged items land on the Notion board as 'New'. Watch what that means.\n")

    candidates = [m for m in matching.compute_matches(conn) if m["item_id"] in triaged]
    print(f"  Matching over the items just triaged: {len(candidates)} matches.")
    print("  Classified, scored, summarised, and still unroutable. Nothing reaches a")
    print("  client until a person approves it. That is the product.\n")

    if not triaged:
        print("  Nothing was triaged, so there is nothing to approve. Stopping.")
        conn.close()
        return 0

    approved = triaged[0]
    conn.execute("UPDATE items SET review_status = 'Reviewed' WHERE id = ?", (approved,))
    conn.commit()
    print(f"  A reviewer approves item {approved}. (Simulated: a demo cannot wait for")
    print("  a human. In production this comes back from Notion via `notion_sync pull`.)")

    # --- match ---
    rule("STAGE 4  MATCH  (deterministic: tag overlap and a level gate. No AI.)")
    results = [m for m in matching.compute_matches(conn) if m["item_id"] in triaged]
    if not results:
        print("  No matches. The approved item shares no tag with any client profile,")
        print("  or it sits below every client's minimum level. The rule working, not a bug.")
        conn.close()
        return 0

    for m in results:
        print(f"  [{m['score']:>4.1f}] item {m['item_id']} ({m['level']}) -> {m['client_name']}")
        print(f"         because {m['matched_on']}")
        conn.execute(
            "INSERT INTO matches (item_id, client_id, score, matched_on, created_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(item_id, client_id) DO UPDATE SET "
            "score = excluded.score, matched_on = excluded.matched_on",
            (m["item_id"], m["client_id"], m["score"], m["matched_on"],
             datetime.now(timezone.utc).isoformat()),
        )
    conn.commit()

    # --- distribute ---
    rule("STAGE 5  DISTRIBUTE")
    client = conn.execute("SELECT id, name FROM clients WHERE id = ?",
                          (results[0]["client_id"],)).fetchone()
    print(f"Digest for {client['name']}. The summary is the one triage wrote and the")
    print("reviewer approved. Distribution makes NO model call.\n")

    digest.distribute_client(conn, client, channels.ConsoleChannel(), on_date, send=True)

    print("\n  Running distribution again, immediately:")
    again = digest.distribute_client(conn, client, channels.ConsoleChannel(),
                                     on_date, send=True)
    print(f"  -> {again['items']} items sent. delivered_at means nothing is ever sent twice.")

    rule("DEMO COMPLETE")
    print(f"Ran on {demo_db}. finalogic.db was never written to.")
    conn.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Live end-to-end demo of the pipeline.")
    parser.add_argument("--limit", type=int, default=3,
                        help="how many items to triage (default 3, a few cents)")
    parser.add_argument("--no-collect", action="store_true",
                        help="skip the live fetch and use what is already stored")
    parser.add_argument("--no-rewind", action="store_true",
                        help="do not reset the copy's triage state; triage only items "
                             "that are genuinely untriaged. The demo will run out of "
                             "material once the backlog is cleared.")
    parser.add_argument("--date", default=DEMO_DATE.isoformat(), metavar="YYYY-MM-DD",
                        help=f"the date the demo presents itself as running on "
                             f"(default {DEMO_DATE.isoformat()}). Fixed rather than "
                             f"today's date so the demo log and digest are reproducible.")
    args = parser.parse_args()

    try:
        on_date = date.fromisoformat(args.date)
    except ValueError:
        raise SystemExit(f"--date must be YYYY-MM-DD, got {args.date!r}")

    return demo(limit=args.limit, collect=not args.no_collect,
                rewind_first=not args.no_rewind, on_date=on_date)


if __name__ == "__main__":
    sys.exit(main())
