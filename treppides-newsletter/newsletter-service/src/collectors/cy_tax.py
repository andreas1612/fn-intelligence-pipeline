"""Cyprus Tax Department scraper (authority, Cyprus). Ministry of Finance Domino
site. No RSS. The announcements listing renders items as text nodes shaped:

    "<bullet> DD/MM/YYYY <title>"   with a link to .../All/<GUID>?OpenDocument

Notes:
  - mof.gov.cy serves an incomplete TLS chain that Python rejects; we fetch this
    host with verify=False (read-only public gov site).
  - Item pages are HTML but on the same broken-TLS host, so triage's article
    fetch will fall back to the title. The titles are descriptive (DAC8, CRS,
    bond-yield rates), which is enough to tag direct/international tax.
  - A min-year guard avoids importing very old circulars if a circulars listing
    (which is sorted oldest-first) is added later.
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

_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_PREFIX = re.compile(r"^[^0-9A-Za-z]*\d{1,2}/\d{1,2}/\d{4}\s*")
MIN_YEAR = 2024


def _fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": config.BROWSER_UA},
                        timeout=30, verify=False)
    resp.raise_for_status()
    return resp.text


def _container_with_link(node):
    cur = node.parent
    for _ in range(3):
        if cur is None:
            return None
        if cur.find("a", href=True):
            return cur
        cur = cur.parent
    return None


def collect(conn, source: dict) -> dict:
    urls = source.get("urls") or [source["url"]]
    new_count = 0
    seen = 0
    newest: str | None = None
    retrieved = utc_now_iso()

    for base in urls:
        soup = BeautifulSoup(_fetch(base), "html.parser")
        for node in soup.find_all(string=_DATE):
            cont = _container_with_link(node)
            if not cont:
                continue
            link = cont.find(
                "a", href=re.compile(r"OpenDocument|/All/", re.I))
            if not link:
                continue
            txt = re.sub(r"\s+", " ", cont.get_text(" ", strip=True))
            m = _DATE.search(txt)
            if not m:
                continue
            d, mo, yr = (int(x) for x in m.groups())
            if yr < MIN_YEAR:
                continue
            try:
                iso = datetime(yr, mo, d, tzinfo=timezone.utc).isoformat()
            except ValueError:
                iso = None
            title = _PREFIX.sub("", txt).strip()
            if len(title) < 10:
                continue
            seen += 1
            url = urljoin(base, link["href"])
            if iso and (newest is None or iso > newest):
                newest = iso
            item = {
                "source": source["key"],
                "source_category": source["category"],
                "title": title,
                "url": url,
                "published_at": iso,
                "retrieved_at": retrieved,
                "summary": title,  # body on broken-TLS host; title is the triage text
                "content_hash": content_hash(title, url),
            }
            if insert_item(conn, item):
                new_count += 1

    conn.commit()
    update_sync_state(conn, source["key"], new_count, seen, newest)
    return {"source": source["key"], "category": source["category"],
            "seen": seen, "new": new_count, "newest": newest}
