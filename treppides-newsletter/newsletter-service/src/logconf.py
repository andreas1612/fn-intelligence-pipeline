"""Central logging: rotating file (logs/newsletter.log) + console.

Use get_logger(name) anywhere. The file handler rotates at 2 MB, keeps 5 backups,
so nightly runs never grow the log unbounded.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from . import config

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    config.ensure_dirs()
    root = logging.getLogger("newsletter")
    root.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    fh = RotatingFileHandler(config.LOGS_DIR / "newsletter.log",
                             maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    root.handlers.clear()
    root.addHandler(fh)
    root.addHandler(ch)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(f"newsletter.{name}")
