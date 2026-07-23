"""Triage: tag each untriaged item against taxonomy.md via the LLM. Autonomous.

Idempotent + cheap to re-run: only rows with triaged_at IS NULL are processed,
so repeated test runs never re-spend on an already-tagged item.

Full autonomy handling: low-confidence items and anything tagged 'other' are
marked archived=1 (kept, queryable, but routed to no department) since there is
no human review gate. Journal items are capped below Urgent.

    python -m src.triage            # triage all untriaged
    python -m src.triage --limit 5  # bound a run (shakedown)
    python -m src.triage --retriage # clear triage and redo everything (spends!)
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config
from .db import connect, fetch_untriaged, init_db, utc_now_iso
from .fetch import fetch_article_text
from .llm import LLMError, generate_json

# Controlled vocabulary. MUST match taxonomy.md (v0.1). If the taxonomy changes,
# update here too - validation rejects anything outside these sets.
THEMES = {
    "direct-tax", "vat", "transfer-pricing", "international-tax", "tax-administration",
    "auditing-standards", "audit-quality", "ethics-independence",
    "ifrs", "financial-reporting", "sustainability-reporting",
    "aml-cft", "investment-firm-regulation", "licensing-authorisation",
    "regulatory-compliance-risk", "payments", "fund-regulation", "fund-administration",
    "company-law", "registrar-filings",
    "ict-operational-resilience", "cybersecurity", "data-protection", "ai-regulation",
    "employment-law", "social-insurance-payroll",
    "economic-general", "other",
}
JURISDICTIONS = {"cyprus", "eu", "international"}
TYPES = {
    "legislation", "guidelines-standards", "consultation", "circular-supervisory",
    "enforcement", "report-publication", "news-commentary",
}
LEVELS = {"Urgent", "High", "Standard", "Low"}
LEVEL_RANK = {"Low": 0, "Standard": 1, "High": 2, "Urgent": 3}


def _load_prompt_template() -> str:
    with open(config.SERVICE_ROOT / "src" / "triage_prompt.md", encoding="utf-8") as f:
        return f.read()


def _load_taxonomy() -> str:
    with open(config.TAXONOMY_PATH, encoding="utf-8") as f:
        return f.read()


def build_prompt(template: str, taxonomy: str, item, text: str) -> str:
    return (
        template
        .replace("{{TAXONOMY}}", taxonomy)
        .replace("{{SOURCE}}", item["source"])
        .replace("{{CATEGORY}}", item["source_category"])
        .replace("{{TITLE}}", item["title"])
        .replace("{{PUBLISHED_AT}}", item["published_at"] or "unknown")
        .replace("{{TEXT}}", text)
    )


def validate(data: dict, category: str) -> dict:
    """Coerce model output to the controlled vocabulary. Never trust blindly."""
    themes = [t for t in (data.get("theme_tags") or []) if t in THEMES][:3]
    if not themes:
        themes = ["other"]

    juris = data.get("jurisdiction")
    juris = juris if juris in JURISDICTIONS else None

    dtype = data.get("doc_type")
    dtype = dtype if dtype in TYPES else "report-publication"

    level = data.get("level")
    level = level if level in LEVELS else "Standard"

    conf = data.get("confidence")
    conf = conf if conf in {"high", "medium", "low"} else "low"

    # Journal cap: never Urgent from a journal alone.
    if category == "journal" and level == "Urgent":
        level = "High"

    # Archive rule (full autonomy, no human gate): drop only what cannot route or
    # is untrusted noise. 'other' has no routable theme. A journal item at low
    # confidence is noise. But an authority item with a real theme is kept even at
    # low confidence - a trusted source beats a thin summary (e.g. CySEC items
    # tagged from the title because the body is a PDF).
    archived = 1 if "other" in themes else 0
    if category == "journal" and conf == "low":
        archived = 1

    return {
        "theme_tags": themes,
        "jurisdiction": juris,
        "doc_type": dtype,
        "level": level,
        "confidence": conf,
        "ai_summary": (data.get("summary") or "").strip(),
        "archived": archived,
    }


def triage_item(conn, item, template, taxonomy) -> dict:
    # Fetch the full article; fall back to the feed snippet if it fails.
    article_text, fetch_status = fetch_article_text(item["url"])
    text_for_model = article_text or item["summary"] or item["title"] or ""
    prompt = build_prompt(template, taxonomy, item, text_for_model)
    try:
        res = generate_json(prompt)
        v = validate(res["data"], item["source_category"])
        in_tok, out_tok = res["input_tokens"], res["output_tokens"]
    except LLMError as e:
        # Autonomous failure handling: mark triaged, archived, low confidence.
        v = {"theme_tags": ["other"], "jurisdiction": None,
             "doc_type": "report-publication", "level": "Low",
             "confidence": "low", "ai_summary": f"[triage error: {e}]",
             "archived": 1}
        in_tok = out_tok = 0

    conn.execute(
        """
        UPDATE items SET
            triaged_at=?, theme_tags=?, jurisdiction=?, doc_type=?, level=?,
            confidence=?, ai_summary=?, fetch_status=?, archived=?, model=?,
            input_tokens=?, output_tokens=?
        WHERE id=?
        """,
        (utc_now_iso(), json.dumps(v["theme_tags"]), v["jurisdiction"],
         v["doc_type"], v["level"], v["confidence"], v["ai_summary"],
         fetch_status, v["archived"], config.KIE_MODEL, in_tok, out_tok, item["id"]),
    )
    conn.commit()
    return {"id": item["id"], **v, "fetch_status": fetch_status,
            "input_tokens": in_tok, "output_tokens": out_tok}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--retriage", action="store_true",
                    help="clear all triage and redo (spends credits)")
    args = ap.parse_args()

    conn = connect()
    init_db(conn)

    if args.retriage:
        conn.execute("UPDATE items SET triaged_at=NULL")
        conn.execute("DELETE FROM routes")
        conn.commit()

    items = fetch_untriaged(conn, args.limit)
    if not items:
        print("Nothing to triage (all items already tagged).")
        return 0

    template, taxonomy = _load_prompt_template(), _load_taxonomy()
    tot_in = tot_out = 0
    archived = 0
    print(f"Triaging {len(items)} item(s)...\n")
    for it in items:
        r = triage_item(conn, it, template, taxonomy)
        tot_in += r["input_tokens"]
        tot_out += r["output_tokens"]
        archived += r["archived"]
        flag = "  [archived]" if r["archived"] else ""
        print(f"  #{r['id']:3} {r['level']:8} {'/'.join(r['theme_tags']):40} "
              f"{it['source']}{flag}")

    config.ensure_dirs()
    run = {"ts": utc_now_iso(), "triaged": len(items), "archived": archived,
           "input_tokens": tot_in, "output_tokens": tot_out, "model": config.KIE_MODEL}
    with open(config.LOGS_DIR / "triage_runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(run) + "\n")

    print(f"\nTriaged {len(items)} ({archived} archived). "
          f"Tokens in={tot_in} out={tot_out}. Model={config.KIE_MODEL}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
