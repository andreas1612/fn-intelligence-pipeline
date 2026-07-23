"""Config-driven HTML listing scraper. For server-rendered "list of items" pages
where each item has a title, a link, and a date. Selectors live in sources.yaml,
so a new simple site is a config entry, not new code. (CySEC and cy_tax stay as
bespoke modules because of their quirks.)

sources.yaml keys used:
  url            listing page URL
  verify         false to skip TLS verify (broken-chain gov sites)
  limit          max items to take (listings can be huge)
  min_year       skip items older than this year (optional)
  item_selector  CSS selector for each item block
  title_selector CSS selector for the title (text, or its 'title' attr) [default: the link]
  link_selector  CSS selector for the <a> whose href is the item URL [default: 'a']
  date_selector  CSS selector for a text date (parsed with date_format)
  date_format    strptime format for date_selector text (e.g. '%d %B %Y')
  date_attr_selector  CSS selector for an element carrying a 'datetime' ISO attr
  summary_selector    CSS selector for summary text (optional; falls back to title)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

from .. import config
from ..db import content_hash, insert_item, update_sync_state, utc_now_iso

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _text(el) -> str:
    if not el:
        return ""
    t = el.get_text(strip=True)
    return t or (el.get("title") or "")


def _parse_date(block, src) -> str | None:
    sel = src.get("date_attr_selector")
    if sel:
        el = block.select_one(sel)
        if el and el.get("datetime"):
            try:
                d = datetime.fromisoformat(el["datetime"][:10])
                return d.replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass
    sel = src.get("date_selector")
    fmt = src.get("date_format")
    if sel and fmt:
        el = block.select_one(sel)
        if el:
            try:
                d = datetime.strptime(el.get_text(strip=True), fmt)
                return d.replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass
    return None


def collect(conn, source: dict) -> dict:
    verify = source.get("verify", True)
    limit = int(source.get("limit", 30))
    min_year = source.get("min_year")
    resp = requests.get(source["url"], headers={"User-Agent": config.BROWSER_UA},
                        timeout=30, verify=verify)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    blocks = soup.select(source["item_selector"])[:limit]
    new_count = 0
    seen = 0
    newest = None
    retrieved = utc_now_iso()

    for b in blocks:
        link = b.select_one(source.get("link_selector", "a"))
        if not (link and link.get("href")):
            continue
        title_el = b.select_one(source["title_selector"]) if source.get("title_selector") else link
        title = _text(title_el)
        if len(title) < 8:
            continue
        iso = _parse_date(b, source)
        if min_year and iso and int(iso[:4]) < int(min_year):
            continue
        seen += 1
        url = urljoin(source["url"], link["href"])
        summary = _text(b.select_one(source["summary_selector"])) if source.get("summary_selector") else title
        if iso and (newest is None or iso > newest):
            newest = iso
        item = {
            "source": source["key"],
            "source_category": source["category"],
            "title": title,
            "url": url,
            "published_at": iso,
            "retrieved_at": retrieved,
            "summary": summary or title,
            "content_hash": content_hash(title, url),
        }
        if insert_item(conn, item):
            new_count += 1

    conn.commit()
    update_sync_state(conn, source["key"], new_count, seen, newest)
    return {"source": source["key"], "category": source["category"],
            "seen": seen, "new": new_count, "newest": newest}
