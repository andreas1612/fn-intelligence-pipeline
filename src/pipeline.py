"""Full-cycle orchestrator: collect, triage, push, pull, match, distribute (D-024).

Runs the stages in order and stops on the first failure, because every stage
depends on the one before it. Each stage remains independently runnable; this
module adds sequencing, not new behaviour.

The human gate sits inside the cycle, not around it. push sends triaged items to
the Notion board and pull reads the review decisions back. Anything a person has
not marked Reviewed or Published simply does not match, and so is never
distributed. A full run is therefore safe to schedule: it cannot outrun the
reviewer, it can only wait for them.

Two stages cost money or send things, so both are opt-in:
    triage      calls the Claude API, one request per untriaged item
    distribute  delivers via the configured channel and marks matches delivered

Run with:
    python -m src.pipeline --dry-run              # preview the whole cycle, no writes
    python -m src.pipeline                        # collect, push, pull, match (safe stages)
    python -m src.pipeline --triage --distribute  # the full cycle
    python -m src.pipeline --only match distribute
    python -m src.pipeline --skip collect
"""

import argparse
import sqlite3
import sys
import traceback
from datetime import datetime, timezone

from src import clients as clients_module
from src import db, matching, migrate, notion_sync, run as collect_run, triage
from src.collectors.base import logger
from src.distribute import channels, digest

STAGES = ("collect", "triage", "push", "pull", "match", "distribute")

# Stages that reach outside the repository or spend money. Off unless asked for.
OPT_IN = ("triage", "distribute")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Stages ---------------------------------------------------------------
#
# Each returns an exit code: 0 success, non-zero failure. A dry run must not
# write, send, or call a model, so each stage reports what it would do instead.


def stage_collect(dry_run: bool) -> int:
    if dry_run:
        conn = db.connect()
        before = conn.execute("SELECT count(*) FROM items").fetchone()[0]
        conn.close()
        print(f"  would run {len(collect_run.COLLECTORS)} collector(s): "
              f"{', '.join(collect_run.COLLECTORS)}")
        print(f"  {before} item(s) currently stored")
        return 0
    return collect_run.run()


def stage_triage(dry_run: bool) -> int:
    # triage.run already has a dry-run mode: it fetches pages and builds prompts
    # but makes no API call and writes nothing.
    return triage.run(dry_run=dry_run)


def stage_push(dry_run: bool) -> int:
    if dry_run:
        conn = db.connect()
        conn.row_factory = sqlite3.Row
        migrate.migrate(conn)
        pending = conn.execute(
            "SELECT count(*) FROM items WHERE triaged_at IS NOT NULL AND notion_page_id IS NULL"
        ).fetchone()[0]
        conn.close()
        print(f"  would push {pending} triaged item(s) to the Notion review board")
        return 0
    return notion_sync.push()


def stage_pull(dry_run: bool) -> int:
    if dry_run:
        conn = db.connect()
        conn.row_factory = sqlite3.Row
        migrate.migrate(conn)
        pages = conn.execute(
            "SELECT count(*) FROM items WHERE notion_page_id IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        print(f"  would read {pages} Notion page(s) back for Status and Level")
        return 0
    return notion_sync.pull()


def stage_match(dry_run: bool) -> int:
    # matching.run(preview=True) matches every triaged item and writes nothing.
    # The real run is restricted to Reviewed and Published items (the human gate).
    if dry_run:
        return matching.run(preview=True)
    return matching.run()


def stage_distribute(dry_run: bool) -> int:
    # send=False prints each digest and marks nothing.
    return digest.run(all_clients=True, send=not dry_run)


STAGE_FUNCTIONS = {
    "collect": stage_collect,
    "triage": stage_triage,
    "push": stage_push,
    "pull": stage_pull,
    "match": stage_match,
    "distribute": stage_distribute,
}


# --- Run ------------------------------------------------------------------


def selected_stages(only: list[str] | None, skip: list[str] | None,
                    triage_on: bool, distribute_on: bool, dry_run: bool) -> list[str]:
    if only:
        return [s for s in STAGES if s in only]

    chosen = list(STAGES)

    # A dry run cannot spend money or send anything, so the opt-in stages are
    # safe to preview by default. A real run must be asked for explicitly.
    if not dry_run:
        if not triage_on:
            chosen.remove("triage")
        if not distribute_on:
            chosen.remove("distribute")

    if skip:
        chosen = [s for s in chosen if s not in skip]
    return chosen


def run(only=None, skip=None, triage_on=False, distribute_on=False, dry_run=False) -> int:
    stages = selected_stages(only, skip, triage_on, distribute_on, dry_run)

    mode = "DRY RUN, nothing is written, sent, or charged" if dry_run else "LIVE"
    print(f"\n=== Finalogic pipeline: {mode} ===")
    print(f"Started {now_iso()}")
    print(f"Stages: {' -> '.join(stages) if stages else '(none)'}")

    if not dry_run:
        omitted = [s for s in OPT_IN if s not in stages]
        if omitted:
            print(f"Not running: {', '.join(omitted)} "
                  f"(opt in with {' '.join('--' + s for s in omitted)})")

    outcomes: list[tuple[str, str]] = []
    for stage in stages:
        print(f"\n--- {stage} ---")
        try:
            code = STAGE_FUNCTIONS[stage](dry_run)
        except SystemExit as exc:
            # A stage raises SystemExit for a missing key or an unseeded client
            # register. That is a configuration problem, not a crash.
            code = exc.code if isinstance(exc.code, int) else 1
            if exc.code and not isinstance(exc.code, int):
                print(exc.code)
        except Exception:
            logger.error("stage=%s crashed", stage)
            traceback.print_exc()
            code = 1

        if code != 0:
            outcomes.append((stage, "FAILED"))
            print_summary(outcomes, stopped_at=stage)
            # Later stages consume this stage's output, so continuing would
            # distribute against a half-built ledger.
            return code

        outcomes.append((stage, "ok"))

    print_summary(outcomes)
    return 0


def print_summary(outcomes: list[tuple[str, str]], stopped_at: str | None = None) -> None:
    print("\n=== Pipeline summary ===")
    for stage, status in outcomes:
        print(f"  {stage:<11} {status}")
    if stopped_at:
        remaining = STAGES[STAGES.index(stopped_at) + 1:]
        print(f"\nStopped at {stopped_at}. Not run: {', '.join(remaining) or '(none)'}.")
        print("Later stages consume earlier output, so the cycle stops rather than "
              "running on partial data.")
    print(f"Finished {now_iso()}")


def main() -> int:
    channels.force_utf8_stdout()

    parser = argparse.ArgumentParser(
        description="Run the full intelligence cycle: "
                    "collect, triage, push, pull, match, distribute.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview every stage. No API calls, no writes, no sends, no cost.",
    )
    parser.add_argument(
        "--triage",
        action="store_true",
        help="include the triage stage. Calls the Claude API and costs money.",
    )
    parser.add_argument(
        "--distribute",
        action="store_true",
        help="include the distribute stage. Delivers digests and marks them delivered.",
    )
    parser.add_argument(
        "--only", nargs="+", choices=STAGES, metavar="STAGE",
        help=f"run only these stages, in pipeline order. Choices: {', '.join(STAGES)}",
    )
    parser.add_argument(
        "--skip", nargs="+", choices=STAGES, metavar="STAGE",
        help="run every stage except these",
    )
    args = parser.parse_args()

    return run(
        only=args.only,
        skip=args.skip,
        triage_on=args.triage,
        distribute_on=args.distribute,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
