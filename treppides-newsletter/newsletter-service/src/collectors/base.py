"""Generic RSS collector. All Phase B sources are RSS, so one parametrised
collector covers them; per-source modules can override later if a feed is odd.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import feedparser
import requests

from .. import config
from ..db import content_hash, insert_item, update_sync_state, utc_now_iso


def _to_iso(struct_time) -> str | None:
    if not struct_time:
        return None
    try:
        return datetime(*struct_time[:6], tzinfo=timezone.utc).isoformat()
    except Exception:
        return None


def fetch_feed(url: str) -> feedparser.FeedParserDict:
    """Fetch with a real UA (feedparser alone gets 403 from some sites), then parse."""
    resp = requests.get(url, headers={"User-Agent": config.BROWSER_UA}, timeout=20)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def collect_source(conn, source: dict) -> dict:
    """Collect one RSS source. Returns stats. Raises on hard fetch failure."""
    parsed = fetch_feed(source["url"])
    entries = parsed.entries or []

    new_count = 0
    newest_pub: str | None = None
    retrieved = utc_now_iso()

    for e in entries:
        title = (e.get("title") or "").strip()
        url = (e.get("link") or "").strip()
        if not title or not url:
            continue
        pub = _to_iso(e.get("published_parsed")) or _to_iso(e.get("updated_parsed"))
        if pub and (newest_pub is None or pub > newest_pub):
            newest_pub = pub
        summary = (e.get("summary") or "").strip()

        item = {
            "source": source["key"],
            "source_category": source["category"],
            "title": title,
            "url": url,
            "published_at": pub,
            "retrieved_at": retrieved,
            "summary": summary,
            "content_hash": content_hash(title, url),
        }
        if insert_item(conn, item):
            new_count += 1

    conn.commit()
    update_sync_state(conn, source["key"], new_count, len(entries), newest_pub)

    return {
        "source": source["key"],
        "category": source["category"],
        "seen": len(entries),
        "new": new_count,
        "newest": newest_pub,
    }
