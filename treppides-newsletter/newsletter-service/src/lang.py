"""Language gate: only English and Greek content enters the pipeline.

langdetect alone is unreliable on short titles in BOTH directions ("bank holiday"
-> Somali 0.99; "EIOPA consults on ..." -> misread as non-English). So we use a
hybrid, biased toward keeping English:

  1. Greek characters  -> keep (Greek).
  2. A distinctly-English function word in the title (the, of, to, for, on, ...)
     -> keep. These words are rare in Italian/French/Spanish/German, so their
     presence is a strong, reliable English signal.
  3. No English marker and the title is short -> keep (can't judge reliably).
  4. No English marker and the title is long enough -> ask langdetect, and drop
     only if it is reasonably confident the language is not English or Greek.

Judged on the TITLE (the item's own language); a body can be multilingual while
the item itself is English.
"""
from __future__ import annotations

import re

from langdetect import DetectorFactory, detect_langs

DetectorFactory.seed = 0

_ALLOWED = {"en", "el"}
_MIN_CHARS = 40

# Distinctly-English function words (deliberately excludes in/a/as/di which are
# shared with Romance languages).
_EN_MARKERS = {
    "the", "of", "to", "and", "for", "with", "from", "on", "is", "are", "by",
    "new", "its", "be", "this", "that", "will", "has", "have", "into", "over",
    "under", "not", "consults", "publishes", "guidance", "report",
}


def _has_greek(text: str) -> bool:
    return any(0x0370 <= ord(ch) <= 0x03FF or 0x1F00 <= ord(ch) <= 0x1FFF
               for ch in text)


def is_allowed(title: str, summary: str = "") -> bool:
    title = (title or "").strip()
    if _has_greek(title):
        return True
    words = set(re.findall(r"[a-z]+", title.lower()))
    if words & _EN_MARKERS:
        return True  # strong English signal
    if len(title) < _MIN_CHARS:
        return True  # too short to judge reliably
    try:
        top = detect_langs(title.lower())[0]
    except Exception:
        return True
    if top.lang in _ALLOWED:
        return True
    return top.prob < 0.80
