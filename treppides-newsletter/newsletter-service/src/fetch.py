"""Fetch an article page and reduce it to readable text for triage.

Triaging on the full article (not just the RSS title+summary) is what stops
thin summaries from archiving as low-confidence. On any failure we return
(None, reason) and triage falls back to the feed snippet - the item is never
skipped.
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from . import config

FETCH_CHAR_CAP = 15000
_DROP_TAGS = ["script", "style", "nav", "header", "footer", "aside", "form",
              "noscript", "svg", "button"]


def fetch_article_text(url: str) -> tuple[str | None, str]:
    """Return (readable_text_or_None, status). status is 'ok' or a short reason."""
    # Skip URLs that are clearly not HTML (e.g. CySEC's GetFile.aspx PDFs). No
    # point downloading a body we can't parse; triage falls back to the title.
    low = url.lower()
    if low.endswith(".pdf") or "getfile.aspx" in low or "/getfile" in low:
        return None, "skipped_binary"
    try:
        resp = requests.get(
            url, headers={"User-Agent": config.BROWSER_UA}, timeout=(10, 25)
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return None, f"fetch_error:{type(e).__name__}"

    ctype = resp.headers.get("Content-Type", "").lower()
    if "html" not in ctype and "xml" not in ctype and "text" not in ctype:
        return None, f"non_html:{ctype[:30]}"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(_DROP_TAGS):
        tag.decompose()

    # Prefer the main content region if the page marks one.
    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = re.sub(r"\s+", " ", main.get_text(separator=" ", strip=True)).strip()

    if len(text) < 200:
        return None, "empty_content"
    return text[:FETCH_CHAR_CAP], "ok"
