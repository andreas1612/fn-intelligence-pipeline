# Treppides Newsletter Service

A standalone service that collects regulatory & industry publications, tags each
item with AI against a controlled taxonomy, and routes it to the **departments**
that care — so every employee gets a feed scoped to their own department instead
of everyone's noise. Built to plug into the Treppides Hub (see
[../DELIVERABLE.md](../DELIVERABLE.md)); runs standalone today with a department
picker standing in for hub identity.

Adapted from the Finalogic pipeline architecture, but **fully autonomous** (no
human review gate) and re-based on the Treppides audit/tax/accounting domain.

## Pipeline

```
collect ──▶ triage ──▶ match ──▶ serve
(RSS +      (AI tags     (themes→      (web UI / API,
 scrapers)   theme/juris/  department    per-department,
             type/level)   profiles)     2 tabs, search)
```

- **Collect** — RSS feeds + HTML scrapers. Dedups on a content hash; per-source
  high-water mark + health checks. Re-running collects nothing already seen.
- **Triage** — one AI call per item (kie.ai / Gemini, behind `src/llm.py`). Fetches
  the article body, tags theme/jurisdiction/type/level/confidence against
  `../taxonomy.md`. Only ever processes **untriaged** rows, so re-runs never
  re-spend. Low-confidence / `other` items are archived (not shown). No human gate.
- **Match** — deterministic: an item reaches a department only if it shares a
  **theme** with that department's profile (`../departments.yaml`). One item can
  fan out to many departments; each match records why. Journals are capped below
  Urgent and deduped against the authority original.
- **Serve** — FastAPI + a vanilla web page: per-department feed (two tabs,
  Authorities / Journals), plus an Explore mode (search + source filter +
  cross-department view), sortable by date or urgency.

Only **English and Greek** items enter the pipeline (`src/lang.py`); anything else
is dropped at ingest.

## Sources (19)

| Category | Sources |
|---|---|
| **Authorities — scrapers (4)** | CySEC (announcements + general circulars + policy statements), Cyprus Tax Department, Central Bank of Cyprus, Registrar of Companies |
| **Authorities — RSS (11)** | ESMA, EBA, EDPB, European Commission (Digital/AI), EIOPA, ECB Banking Supervision (SSM), NCSC UK, IAASB, IESBA, IFAC, FSB |
| **Journals — RSS (4)** | Accountancy Europe, Finance Magnates, AccountancyAge, Tax Foundation |

Full register (incl. deferred sources) in [../sources.md](../sources.md).
**Deferred** (need a headless browser or a real API, not a plain GET): MOKAS,
ICPAC, Cyprus DPA, EUR-Lex, IFRS/OECD, and CySEC's JS-rendered sections
(Consultation Papers, Board/Court Decisions, Administrative Sanctions, Warnings).

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env      # fill KIE_API_KEY
```

Run the stages:

```powershell
python -m src.run                       # collect
python -m src.triage                    # tag untriaged items (spends kie credits)
python -m src.match                     # route to departments
python -m src.simulate --list           # list department feeds
python -m src.simulate --department "Taxation" --sub "VAT"

# Web UI (department picker + Explore/search) at http://127.0.0.1:8004/
python -m uvicorn src.webapp:app --port 8004
```

### The whole cycle

```powershell
python -m src.pipeline --force          # collect -> triage -> match, logged
```

`python -m src.pipeline` (without `--force`) is the **nightly** entry point and is
a **no-op until `SCHEDULE_ENABLED=true`**. See [scripts/schedule.md](scripts/schedule.md)
to register the (currently disabled) daily task.

### Testing helpers

```powershell
python -m src.reset --routes --yes      # clear routes (re-match is free)
python -m src.reset --triage --yes      # clear triage + routes (re-triage SPENDS)
python -m src.reset --all --yes         # wipe everything, start fresh
```

## Config (the controlled inputs, one dir up)

| File | What it controls |
|---|---|
| [../taxonomy.md](../taxonomy.md) | The tag vocabulary (themes/jurisdiction/type). Routing keys off themes. |
| [../departments.yaml](../departments.yaml) | Each department → the themes it receives. |
| [../sources.md](../sources.md) | Human-readable source register. |
| `config/sources.yaml` | Machine-readable source list the collectors actually run. |

## Layout

```
src/
  db.py            SQLite store (items, sync_state high-water mark, routes) + migrations
  lang.py          language gate (English/Greek only)
  llm.py           the ONLY model-aware code (kie.ai); swap providers here
  fetch.py         article-body fetch (skips PDFs)
  collectors/
    base.py        generic RSS collector
    html_list.py   config-driven HTML scraper (selectors in sources.yaml)
    cysec.py       CySEC scraper (multi-section)
    cy_tax.py      Cyprus Tax Department scraper
  run.py           collect all sources + health checks
  triage.py        AI tagging + validation against the taxonomy
  triage_prompt.md the prompt (taxonomy injected at runtime)
  match.py         deterministic theme → department routing
  simulate.py      CLI preview of any department's feed
  pipeline.py      nightly orchestrator (disabled by default)
  webapp.py        FastAPI: /api/departments, /api/newsletter, /api/sources, /api/items
  logconf.py       rotating file + console logging
static/index.html  the web UI
data/              SQLite DB (gitignored)
logs/              run logs (gitignored)
```

## Operational notes

- **Cost**: kie.ai gemini-3-5-flash, roughly $0.002–0.005 per item; only untriaged
  items are ever charged. Token totals logged to `logs/triage_runs.jsonl`.
- **Dedup / idempotency**: safe to run any stage repeatedly — content-hash dedup on
  collect, untriaged-only triage, idempotent match.
- **Logging**: `logs/newsletter.log` (rotating). The nightly pipeline logs every stage.
- **Model swap**: change `KIE_MODEL` in `.env`; nothing above `src/llm.py` changes.
