"""Deterministic routing: item themes -> department interest profiles.

Context-level, not URL-level: an item reaches a department only if it shares a
THEME with that department's profile (D-028 lesson). Source/jurisdiction never
route on their own. One item can route to many departments.

Idempotent: recomputes routes for all triaged, non-archived items each run.

    python -m src.match
"""
from __future__ import annotations

import json
import sys

from . import config
from .db import connect, init_db, utc_now_iso
from .triage import LEVEL_RANK


def build_profiles() -> list[dict]:
    """One profile per department and per sub-department. Sub-departments inherit
    the parent's themes/min_level unless they override."""
    doc = config.load_departments()
    default_min = (doc.get("defaults") or {}).get("min_level", "Standard")
    profiles = []
    for dept in doc.get("departments", []):
        name = dept["name"]
        p_themes = set(dept.get("themes") or [])
        p_min = dept.get("min_level", default_min)
        # Parent-level profile (sub = '')
        profiles.append({"department": name, "sub": "",
                         "themes": p_themes, "min_level": p_min})
        for sub_name, sub_cfg in (dept.get("subdepartments") or {}).items():
            sub_cfg = sub_cfg or {}
            profiles.append({
                "department": name,
                "sub": sub_name,
                "themes": set(sub_cfg.get("themes") or p_themes),
                "min_level": sub_cfg.get("min_level", p_min),
            })
    return profiles


def main() -> int:
    conn = connect()
    init_db(conn)
    profiles = build_profiles()

    items = conn.execute(
        "SELECT * FROM items WHERE triaged_at IS NOT NULL AND archived = 0"
    ).fetchall()

    conn.execute("DELETE FROM routes")
    routed = 0
    now = utc_now_iso()

    for it in items:
        themes = set(json.loads(it["theme_tags"] or "[]"))
        lvl = LEVEL_RANK.get(it["level"], 1)
        for p in profiles:
            shared = themes & p["themes"]
            if not shared:
                continue
            if lvl < LEVEL_RANK.get(p["min_level"], 1):
                continue
            conn.execute(
                """INSERT OR REPLACE INTO routes
                   (item_id, department, subdepartment, matched_on, score, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (it["id"], p["department"], p["sub"],
                 ", ".join(sorted(shared)), float(len(shared)), now),
            )
            routed += 1
    conn.commit()

    dept_counts = conn.execute(
        """SELECT department, subdepartment, COUNT(*) c
           FROM routes GROUP BY department, subdepartment
           ORDER BY department, subdepartment"""
    ).fetchall()
    print(f"Routed {routed} item-department pairs across "
          f"{len(items)} routable items.\n")
    for r in dept_counts:
        label = r["department"] + (f" / {r['subdepartment']}" if r["subdepartment"] else "")
        print(f"  {label:45} {r['c']}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
