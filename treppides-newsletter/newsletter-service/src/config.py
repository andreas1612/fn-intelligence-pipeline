"""Central paths and config loading for the newsletter service.

The taxonomy and department map are the drafts one level up in planner/newsletter/,
so this service reads the single source of truth rather than keeping copies.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Force UTF-8 stdout/stderr: item titles carry non-ASCII (Greek from Cyprus
# sources, zero-width spaces from EU feeds) that crash a legacy Windows console.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# newsletter-service/
SERVICE_ROOT = Path(__file__).resolve().parent.parent
# planner/newsletter/  (where the spec + config docs live)
NEWSLETTER_ROOT = SERVICE_ROOT.parent

load_dotenv(SERVICE_ROOT / ".env")

# Config documents (single source of truth, one dir up)
TAXONOMY_PATH = NEWSLETTER_ROOT / "taxonomy.md"
DEPARTMENTS_PATH = NEWSLETTER_ROOT / "departments.yaml"

# Service-local config + data
SOURCES_PATH = SERVICE_ROOT / "config" / "sources.yaml"
DATA_DIR = SERVICE_ROOT / "data"
LOGS_DIR = SERVICE_ROOT / "logs"
DB_PATH = DATA_DIR / "newsletter.db"

# kie.ai
KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_BASE_URL = os.environ.get("KIE_BASE_URL", "https://api.kie.ai")
KIE_MODEL = os.environ.get("KIE_MODEL", "gemini-3-5-flash")
KIE_THINKING_LEVEL = os.environ.get("KIE_THINKING_LEVEL", "low")

# Nightly scheduler master switch. Disabled by default: the daily pipeline is a
# no-op until this is explicitly turned on.
SCHEDULE_ENABLED = os.environ.get("SCHEDULE_ENABLED", "false").lower() in (
    "1", "true", "yes", "on")

USER_AGENT = "TreppidesHubNewsletter/0.1 (internal firm intelligence feed)"
# Some sites (IFRS, OECD) reject non-browser agents. Use this for feed + article
# fetches so we are not blocked.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def load_sources() -> list[dict]:
    with open(SOURCES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def load_departments() -> dict:
    with open(DEPARTMENTS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
