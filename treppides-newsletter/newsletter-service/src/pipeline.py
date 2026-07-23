"""Daily pipeline orchestrator: collect -> triage -> match, once per night.

DISABLED by default. `main()` is a no-op unless SCHEDULE_ENABLED is true, so a
scheduler entry can be registered now and safely left dormant until we flip the
switch. Everything is logged to logs/newsletter.log.

No duplicate collection: the collect stage dedups on content_hash and only
inserts genuinely new items; triage only ever processes untriaged rows; match
recomputes routes idempotently. Re-running the cycle never double-collects,
re-triages, or double-charges.

    python -m src.pipeline            # runs only if SCHEDULE_ENABLED is true
    python -m src.pipeline --force    # run the cycle now regardless (manual)
"""
from __future__ import annotations

import subprocess
import sys

from . import config
from .logconf import get_logger

log = get_logger("pipeline")

STAGES = [
    ("collect", ["-m", "src.run"]),
    ("triage", ["-m", "src.triage"]),
    ("match", ["-m", "src.match"]),
]


def run_cycle() -> bool:
    log.info("===== daily cycle start =====")
    for name, args in STAGES:
        log.info("stage '%s' starting", name)
        proc = subprocess.run([sys.executable, *args], cwd=str(config.SERVICE_ROOT),
                              capture_output=True, text=True)
        for line in (proc.stdout or "").splitlines():
            if line.strip():
                log.info("[%s] %s", name, line)
        if proc.returncode != 0:
            log.error("stage '%s' FAILED (rc=%s): %s", name, proc.returncode,
                      (proc.stderr or "")[-800:])
            log.error("aborting cycle - later stages skipped")
            return False
        log.info("stage '%s' ok", name)
    log.info("===== daily cycle done =====")
    return True


def main() -> int:
    force = "--force" in sys.argv
    if not config.SCHEDULE_ENABLED and not force:
        log.info("scheduler DISABLED (SCHEDULE_ENABLED not set) - skipping. "
                 "Use --force to run manually.")
        return 0
    return 0 if run_cycle() else 1


if __name__ == "__main__":
    sys.exit(main())
