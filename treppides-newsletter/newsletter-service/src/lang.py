"""Language gate: only English and Greek content is allowed into the pipeline.

Some feeds (notably the IFAC family) republish standards translated into other
languages (Italian ISA/ISQM, etc.). Those are dropped at collection.

langdetect is unreliable on ALL-CAPS text, so we lowercase before detecting.
When detection is uncertain we keep the item, to avoid dropping legitimate
English titles on a bad guess.
"""
from __future__ import annotations

from langdetect import DetectorFactory, detect_langs

DetectorFactory.seed = 0  # deterministic

_ALLOWED = {"en", "el"}


def _has_greek(text: str) -> bool:
    # Greek and Coptic (U+0370-03FF) + Greek Extended (U+1F00-1FFF).
    return any(0x0370 <= ord(ch) <= 0x03FF or 0x1F00 <= ord(ch) <= 0x1FFF
               for ch in text)


def is_allowed(title: str, summary: str = "") -> bool:
    text = f"{title or ''} {summary or ''}".strip()
    if not text:
        return True
    if _has_greek(text):
        return True
    try:
        top = detect_langs(text.lower())[0]
    except Exception:
        return True  # can't tell -> don't over-filter
    if top.lang in _ALLOWED:
        return True
    return top.prob < 0.90  # uncertain detection -> keep
