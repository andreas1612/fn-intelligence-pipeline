"""CySEC scraper (authority, Cyprus). No RSS - the announcements listing is
server-rendered HTML, one item per `div.col-row.pb-3`:

    <block>  "DD Mon. YYYY <title>"  + a /CMSPages/GetFile.aspx?guid=... PDF link

We collect the Announcements section, which is CySEC's firehose spanning every
subject (CIF, funds, AML, crypto/MiCA, warnings, enforcement). Per the design,
we do NOT route by section - triage tags each item by content and match routes
it. The item URL is the CySEC PDF; the descriptive title is stored as the
summary so triage always has text even though the body is a PDF (the HTML
article-fetch will not parse a PDF and falls back to the title).

Other CySEC sections (Circulars, Consultations, ...) can be added as more URLs
in the same shape later.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .. import config
from ..db import content_hash, insert_item, update_sync_state, utc_now_iso

BASE = "https://www.cysec.gov.cy"
_DATE_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})\s*(.*)$", re.S)


def _parse_block(text: str) -> tuple[str | None, str]:
    """'20 Jul. 2026 Press Release - ...' -> (iso_date, title)."""
    m = _DATE_RE.match(re.sub(r"\s+", " ", text).strip())
    if not m:
        return None, re.sub(r"\s+", " ", text).strip()
    day, mon, yr, title = m.groups()
    try:
        dt = datetime.strptime(f"{day} {mon[:3]} {yr}", "%d %b %Y").replace(
            tzinfo=timezone.utc)
        iso = dt.isoformat()
    except ValueError:
        iso = None
    return iso, title.strip()


def _fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": config.BROWSER_UA}, timeout=30)
    resp.raise_for_status()
    return resp.text


def collect(conn, source: dict) -> dict:
    # Sections: announcements + circulars, each server-rendered the same way.
    # Back-compat: a single url+pages still works.
    sections = source.get("sections") or [
        {"url": source["url"], "pages": source.get("pages", 1)}]
    new_count = 0
    seen = 0
    newest: str | None = None
    retrieved = utc_now_iso()

    page_urls = []
    for sec in sections:
        pages = int(sec.get("pages", 1))
        for p in range(1, pages + 1):
            page_urls.append(sec["url"] if p == 1 else f"{sec['url']}?page={p}")

    for page_url in page_urls:
        soup = BeautifulSoup(_fetch(page_url), "html.parser")
        for block in soup.select("div.col-row.pb-3"):
            link = block.find("a", href=re.compile(r"GetFile\.aspx", re.I))
            if not link:
                continue
            iso, title = _parse_block(block.get_text(" ", strip=True))
            if not title:
                continue
            seen += 1
            url = link["href"]
            if url.startswith("/"):
                url = BASE + url
            if iso and (newest is None or iso > newest):
                newest = iso
            item = {
                "source": source["key"],
                "source_category": source["category"],
                "title": title,
                "url": url,
                "published_at": iso,
                "retrieved_at": retrieved,
                "summary": title,  # body is a PDF; title is the triage text
                "content_hash": content_hash(title, url),
            }
            if insert_item(conn, item):
                new_count += 1

    conn.commit()
    update_sync_state(conn, source["key"], new_count, seen, newest)
    return {"source": source["key"], "category": source["category"],
            "seen": seen, "new": new_count, "newest": newest}
