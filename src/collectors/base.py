"""Shared fetch and normalisation helpers for Wave 1 collectors."""

import logging
from calendar import timegm
from datetime import datetime, timezone

import feedparser

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("collectors")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def struct_time_to_iso(struct_time) -> str | None:
    if struct_time is None:
        return None
    return datetime.fromtimestamp(timegm(struct_time), tz=timezone.utc).isoformat()


def fetch_rss(source: str, feed_url: str) -> list[dict]:
    """Fetch and normalise an RSS/Atom feed into item dicts.

    Raises on malformed feeds with no entries and a non-empty bozo_exception,
    so a broken feed surfaces as a run failure rather than a silent zero-item pass.
    """
    parsed = feedparser.parse(feed_url)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"{source}: failed to parse feed {feed_url}: {parsed.bozo_exception}")

    retrieved_at = now_iso()
    items = []
    for entry in parsed.entries:
        items.append(
            {
                "source": source,
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", "").strip(),
                "published_at": struct_time_to_iso(entry.get("published_parsed")),
                "retrieved_at": retrieved_at,
                "summary": entry.get("summary"),
            }
        )
    return items
