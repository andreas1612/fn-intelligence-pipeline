"""Standalone web UI + read API for the newsletter.

Dev stand-in for hub identity: the page has a DEPARTMENT DROPDOWN instead of
resolving the logged-in user. The eventual hub page is the same view with the
department resolved from /api/me. Read-only over the SQLite the pipeline fills.

    uvicorn src.webapp:app --port 8004        (run from newsletter-service/)
    then open http://127.0.0.1:8004/
"""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .db import connect
from .match import build_profiles

app = FastAPI(title="Treppides Newsletter (standalone)")

_LEVEL_ORDER = {"Urgent": 0, "High": 1, "Standard": 2, "Low": 3}


@app.get("/api/departments")
def departments() -> list[dict]:
    """Every routable feed: parent departments and sub-departments."""
    out = []
    for p in build_profiles():
        out.append({"department": p["department"], "sub": p["sub"]})
    return out


@app.get("/api/newsletter")
def newsletter(department: str, sub: str = "") -> dict:
    conn = connect()
    rows = conn.execute(
        """
        SELECT i.title, i.source, i.source_category, i.level, i.jurisdiction,
               i.doc_type, i.theme_tags, i.ai_summary, i.url, i.published_at,
               r.matched_on
        FROM routes r JOIN items i ON i.id = r.item_id
        WHERE r.department = ? AND r.subdepartment = ?
        """,
        (department, sub or ""),
    ).fetchall()
    conn.close()

    items = []
    for r in rows:
        d = dict(r)
        d["theme_tags"] = json.loads(d["theme_tags"] or "[]")
        items.append(d)
    items.sort(key=lambda i: (_LEVEL_ORDER.get(i["level"], 9), i["source_category"]))

    return {
        "department": department,
        "sub": sub,
        "authority": [i for i in items if i["source_category"] == "authority"],
        "journal": [i for i in items if i["source_category"] == "journal"],
    }


@app.get("/api/sources")
def sources() -> list[dict]:
    """Distinct sources with their category and routable-item count (for the filter)."""
    conn = connect()
    rows = conn.execute(
        """
        SELECT i.source, i.source_category, COUNT(DISTINCT i.id) AS n
        FROM items i JOIN routes r ON r.item_id = i.id
        GROUP BY i.source, i.source_category
        ORDER BY i.source_category, i.source
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/items")
def items(q: str = "", source: str = "", multi: int = 0) -> dict:
    """Explore/search across all routable items. Each item carries the list of
    DISTINCT top-level departments it routes to, so cross-department items are
    visible. multi=1 returns only items in 2+ departments."""
    conn = connect()
    rows = conn.execute(
        """
        SELECT i.id, i.title, i.source, i.source_category, i.level,
               i.jurisdiction, i.doc_type, i.theme_tags, i.ai_summary, i.url,
               i.published_at,
               GROUP_CONCAT(DISTINCT r.department) AS depts,
               COUNT(DISTINCT r.department)        AS dept_count
        FROM items i JOIN routes r ON r.item_id = i.id
        GROUP BY i.id
        """
    ).fetchall()
    conn.close()

    ql = q.strip().lower()
    out = []
    for r in rows:
        d = dict(r)
        if source and d["source"] != source:
            continue
        if ql:
            haystack = " ".join([
                d["title"] or "", d["ai_summary"] or "",
                d["theme_tags"] or "", d["doc_type"] or "", d["jurisdiction"] or "",
            ]).lower()
            if ql not in haystack:
                continue
        if multi and d["dept_count"] < 2:
            continue
        d["theme_tags"] = json.loads(d["theme_tags"] or "[]")
        d["departments"] = sorted((d.pop("depts") or "").split(","))
        out.append(d)

    out.sort(key=lambda i: (-i["dept_count"], _LEVEL_ORDER.get(i["level"], 9)))
    return {"count": len(out), "items": out}


# Static frontend (index.html). Mounted last so /api/* routes take precedence.
app.mount("/", StaticFiles(directory=str(config.SERVICE_ROOT / "static"), html=True),
          name="static")
