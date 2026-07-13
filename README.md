# Finalogic Intelligence Pipeline

Structured regulatory and cybersecurity intelligence for Finalogic Ltd. The
pipeline monitors official sources, triages each item with AI against a
controlled taxonomy, gates everything through human review, and matches approved
intelligence to specific clients by their interest profile.

Internal use first. Designed to support a white-labelled, client-facing service.

---

## 1. Overview

The system answers one question at scale: "which of today's regulatory and cyber
publications matter to which of our clients, and why?"

It runs in five stages, three of them deterministic, with a human gate in the
middle. Nothing reaches a client without a person approving it.

```
  Collect            Triage               Human review        Match                Distribute
  (deterministic)    (AI + validation)    (Notion)            (deterministic)      (roadmap)
  ---------------    -----------------    ---------------     ----------------     ---------------
  EBA, ESMA,     ->  classify, score,  -> reviewer sets   ->  approved items   ->  per-client
  CERT-EU,           summarise against     Status and          matched to           digest and
  CISA KEV           locked taxonomy        Level in Notion     client profiles      urgent alerts
       |                    |                     |                   |
       v                    v                     v                   v
  items table         triage columns        review_status       matches ledger
  (SQLite)            on items              synced back         (SQLite)
```

SQLite is the single system of record. Notion is a human-review view, not the
source of truth. The AI classifies, scores, and summarises only text the
pipeline fetches; it never invents items, tags, or levels.

---

## 2. Principles (hard rules)

1. **Traceability**: every item traces to a named source URL from the source
   register. No open-web browsing, no discovered sources, no generated items.
2. **AI assists, humans decide**: the model classifies, scores, and summarises
   only fetched text. Summaries derive strictly from that text. Nothing is
   distributed without passing the human review gate.
3. **Controlled taxonomy and scoring**: items are tagged only from
   `docs/taxonomy-v1.0.md` and scored only per `docs/scoring-criteria.md`. No ad
   hoc tags or levels. Client profiles are validated against the same taxonomy.
4. **Simple and boring wins**: standard library plus a minimal dependency set.
   No orchestration frameworks, no agent frameworks.
5. **SQLite is the system of record**: one database file, committed after each
   collection run. Notion is a view.
6. **Deterministic where it counts**: collection, matching, and distribution are
   deterministic and explainable. Only triage uses the model.

---

## 3. Architecture

### Stage 1: Collect (`src/run.py`, `src/collectors/`)

Polls a fixed, verified source list and normalises every entry to a common
shape. Each item stores source, title, URL, publication date, retrieval
timestamp, and a content hash. Deduplication is a `UNIQUE` content hash
(`SHA-256` of normalised title + URL) with `INSERT OR IGNORE`.

Sources (Wave 1):

| Source | Type | Feed |
|--------|------|------|
| EBA | RSS | European Banking Authority news |
| ESMA | RSS | European Securities and Markets Authority |
| CERT-EU | RSS | CERT-EU security advisories |
| CISA KEV | JSON | CISA Known Exploited Vulnerabilities catalog |

Health checks make zero-item runs visible and fail the job, so a silently broken
feed is caught rather than passing as a quiet no-op.

### Stage 2: Triage (`src/triage.py`)

One Claude API call per untriaged item. For each item the stage fetches the page
text (falling back to the feed snippet on failure), builds a prompt from
`src/triage_prompt.md` with the taxonomy and scoring criteria injected at
runtime, and asks the model for structured JSON.

The response is validated before anything is written:

- Tags must come from the locked taxonomy (theme, sector, jurisdiction, type).
- Level must be one of Urgent / High / Standard / Low, or null when discarded.
- `rules_applied` must be bare rule IDs from the scoring criteria.
- On a validation failure the stage retries once, carrying the error back to the
  model. On a second failure the item is flagged as "invalid model output" and
  no tags, level, or summary are written. Nothing is invented.

Raw collection columns are never altered by triage. Every run appends a line to
`logs/triage_runs.jsonl` with counts, token usage, and cost.

### Stage 3: Human review (`src/notion_sync.py`)

`push` creates one Notion page per newly triaged item. Reviewers set `Status`
(New / Reviewed / Published / Discarded) and may change `Level`. `pull` reads
those back into SQLite: it updates `review_status` and logs any level change as
an override. An integrity guard refuses to log an override if the write-once
"AI Level" was edited on the board, comparing back to SQLite as the true
original.

### Stage 4: Client matching (`src/clients.py`, `src/matching.py`)

Approved intelligence is routed to clients by matching each item's taxonomy tags
against a client interest profile. This is the "client-specific tag views"
deferred to Phase 6 in the taxonomy (section 9). See section 6 below.

### Stage 5: Distribute (roadmap)

Per-client digests and urgent alerts, driven off the `matches` ledger's
`delivered_at` column. Not yet built. See the roadmap.

---

## 4. Data model

One SQLite file, `finalogic.db`. Additive migrations only; existing columns and
rows are never dropped or altered.

### `items` (collection + triage)

Raw collection columns, written once at collection:

| Column | Notes |
|--------|-------|
| `id` | primary key |
| `source`, `title`, `url` | from the collector |
| `published_at`, `retrieved_at` | ISO 8601 UTC |
| `content_hash` | `UNIQUE`, dedup key |
| `summary` | feed snippet |

Triage columns, added by `src/migrate.py`, written by triage:

`triaged_at`, `auto_discard`, `theme_tags`, `sector_tags`, `jurisdiction`,
`type`, `level`, `rules_applied`, `ai_summary`, `flagged`, `flag_rules`,
`flag_reason`, `confidence`, `fetch_status`, `model`, `input_tokens`,
`output_tokens`, `review_status` (default `New`), `notion_page_id`.

`theme_tags`, `sector_tags`, and `rules_applied` are stored as JSON arrays.

### `overrides` (review audit)

Logged when a reviewer changes an item's level in Notion: `item_id`,
`original_level`, `final_level`, `reason`, `recorded_at`.

### `clients` and profile tables (client register)

Seeded from `config/clients.yaml` by `src/clients.py`:

| Table | Columns |
|-------|---------|
| `clients` | `id`, `name` (UNIQUE), `active`, `min_level` |
| `client_sectors` | `client_id`, `sector_tag` |
| `client_jurisdictions` | `client_id`, `jurisdiction_tag` |
| `client_themes` | `client_id`, `theme_tag` |

### `matches` (routing ledger)

Written by `src/matching.py`. One row per approved item / client pair:

| Column | Notes |
|--------|-------|
| `item_id`, `client_id` | composite primary key |
| `score` | weighted overlap |
| `matched_on` | human-readable reason, e.g. `jurisdiction: EU; sector: Banks and credit institutions; theme: DORA` |
| `created_at` | when matched |
| `delivered_at` | null until distribution sends it |

---

## 5. Repository layout

```
.
├── README.md                     # this file
├── CLAUDE.md                     # working context for Claude Code sessions
├── requirements.txt
├── .env.example                  # copy to .env; secrets go here (gitignored)
├── finalogic.db                  # SQLite system of record (committed, D-008)
├── .github/workflows/collect.yml # daily collection on GitHub Actions
├── config/
│   └── clients.yaml              # client register (interest profiles)
├── docs/
│   ├── DECISIONS.md              # decision log (D-001..; locked choices)
│   ├── ROADMAP.md                # phased build plan and status
│   ├── taxonomy-v1.0.md          # controlled tag vocabulary (locked)
│   ├── scoring-criteria.md       # relevance and urgency rules (locked)
│   ├── finalogic-source-register.md
│   ├── feed-verification.md
│   └── phase3-*.md
├── logs/
│   └── triage_runs.jsonl         # per-run counts, tokens, cost
└── src/
    ├── db.py                     # SQLite schema and item insert
    ├── migrate.py                # additive triage-column migration
    ├── sources.py                # verified feed URLs
    ├── collectors/               # per-source fetch and normalisation
    │   ├── base.py               # shared RSS fetch, logging, timestamps
    │   ├── eba.py, esma.py, cert_eu.py, cisa_kev.py
    ├── run.py                    # run all collectors, report health
    ├── triage.py                 # AI triage, validation, run log
    ├── triage_prompt.md          # approved prompt template
    ├── notion_sync.py            # Notion push and pull, override logging
    ├── clients.py                # client register seeding and validation
    └── matching.py               # deterministic client matching engine
```

---

## 6. Client matching

Matching turns approved intelligence into a per-client queue. It is deterministic
and explainable: no model call, and every match records why it fired.

### Client profiles (`config/clients.yaml`)

Each client has an interest profile built only from taxonomy tags:

```yaml
clients:
  - name: Cyprus EMI
    active: true
    min_level: Standard          # least urgent level this client wants
    sectors:
      - EMIs and payment institutions
    jurisdictions:
      - EU
      - Cyprus
    themes:
      - DORA
      - ICT incident reporting
      - Payments and e-money
      - AML and financial crime
```

Every sector, jurisdiction, theme, and `min_level` is validated against the
locked taxonomy and level set when seeded. An unknown tag fails loudly and
nothing is seeded, so a client profile can never drift from the taxonomy.

### Matching rule

An item matches a client when both hold:

1. **Overlap**: the item shares at least one sector, jurisdiction, or theme with
   the client profile.
2. **Level gate**: the item's level is at least as urgent as the client's
   `min_level`, where Urgent > High > Standard > Low. A client on `Standard`
   receives Urgent, High, and Standard items, but not Low.

The score weights overlap by dimension, since jurisdiction and sector route a
regulatory item more strongly than a shared theme:

```
score = 3.0 * (shared jurisdictions)
      + 2.0 * (shared sectors)
      + 1.0 * (shared themes)
```

Weights are constants at the top of `src/matching.py`.

### The human gate is enforced

`run` matches only items whose `review_status` is `Reviewed` or `Published`, and
skips anything discarded or untriaged. Clients therefore only ever see intel a
person approved. `preview` matches every triaged item without writing, for
testing against the backlog before review has caught up.

### Commands

```bash
python -m src.clients seed        # validate config/clients.yaml and load clients
python -m src.clients list        # show seeded client profiles
python -m src.matching preview    # candidate matches over all triaged items (no writes)
python -m src.matching run        # match reviewed/published items, write the ledger
python -m src.matching report     # matches by client and the undelivered queue
```

`report` output is the operational view: for each client, the items waiting to be
sent, each with its level, score, and the reason it matched.

---

## 7. Taxonomy and scoring (governance)

The controlled vocabulary and the scoring rules are locked documents, not code
constants. The pipeline parses them at runtime, so the code never holds a second
copy that could drift.

- **Taxonomy** (`docs/taxonomy-v1.0.md`): every item gets exactly one Type, one
  Jurisdiction, 1 to 3 Themes, and 0 to 2 Sectors. 15 theme tags, 5 sector tags,
  3 jurisdiction tags, 7 type tags. The triage loader asserts these counts, so a
  mismatch between the document and the parser fails immediately.
- **Scoring** (`docs/scoring-criteria.md`): urgency levels (Urgent / High /
  Standard / Low) and the rule IDs that justify each. Triage requires bare rule
  IDs in `rules_applied`; free text is a validation failure.
- **Change control**: both documents are versioned. Changes require owner
  approval and a version increment. Client profiles and the triage prompt
  reference the current version.

---

## 8. Setup

### Install

```bash
pip install -r requirements.txt
```

Dependencies: `feedparser`, `requests`, `beautifulsoup4`, `anthropic`,
`notion-client`, `python-dotenv`, `pyyaml`.

### Configure secrets

Copy `.env.example` to `.env` and fill in. `.env` is gitignored and must never be
committed. In GitHub Actions these are repository secrets with the same names.

```
ANTHROPIC_API_KEY=
NOTION_API_KEY=
NOTION_DATABASE_ID=
```

### Create the Notion review board (once)

```bash
python -m src.notion_sync create --parent-page-id <notion-page-id>
```

This prints a `NOTION_DATABASE_ID` to add to `.env`. The board schema (select
and multi-select options) is generated from the locked taxonomy, so it cannot
drift from the tags.

---

## 9. Running the pipeline

Run the stages in order. Each stage is idempotent and safe to re-run.

```bash
# 1. Collect (also runs daily on GitHub Actions)
python -m src.run

# 2. Triage untriaged items
python -m src.triage run                 # add --limit N to bound a run
python -m src.triage run --dry-run       # build prompts, no API calls, no writes

# 3. Human review
python -m src.notion_sync push           # create pages for newly triaged items
#    ... reviewers set Status and Level in Notion ...
python -m src.notion_sync pull           # read Status/Level back, log overrides

# 4. Seed clients (once, and whenever config/clients.yaml changes)
python -m src.clients seed

# 5. Match approved items to clients
python -m src.matching run
python -m src.matching report
```

Matching should run after `notion_sync pull`, since the pull is what sets
`review_status`. Use `python -m src.matching preview` at any time to see how
matching would behave over the full triaged backlog.

---

## 10. Automation

`.github/workflows/collect.yml` runs collection daily at 06:00 UTC (and on
manual dispatch). It installs dependencies, runs the collectors, commits
`finalogic.db` if it changed, and fails the job if any collector reports a health
issue. Secrets are provided as repository secrets, never committed.

Triage, review sync, and matching are run deliberately (they cost tokens or
require human input), so they are not on the daily schedule.

---

## 11. Operational notes

- **Cost tracking**: `logs/triage_runs.jsonl` records tokens and USD per run.
  Pricing constants are in `src/triage.py`.
- **KEV volume**: the CISA KEV catalog is large and returned in full each fetch.
  Deduplication handles storage. A cutoff date gates which KEV items are eligible
  for (paid) triage, so the backlog is not triaged wholesale. The cutoff is a
  constant in `src/triage.py`.
- **Model**: triage uses `claude-sonnet-4-6`. If moving to a newer model
  (for example `claude-sonnet-5`), note that `temperature=0` in `src/triage.py`
  must be removed, since non-default sampling parameters are rejected on newer
  models.
- **Console encoding**: the client tooling forces UTF-8 stdout so item titles
  with non-ASCII characters (Greek from Cyprus sources, zero-width spaces from
  EBA) print without crashing on a legacy Windows console.

---

## 12. Known limitations and next steps

- **Database in git**: `finalogic.db` is committed and rewritten by the daily
  Action. This is fine at proof-of-concept scale (decision D-008), but before a
  client-facing launch it should move to a hosted database. The git history
  bloats with a daily binary blob, and a scheduled run overlapping a manual
  dispatch could race on `git push`.
- **Distribution not built**: stage 5 is the roadmap. The `matches.delivered_at`
  column is the hook. The plan is per-client digests and urgent alerts.
- **Newsletter ingestion**: current collectors are RSS and JSON feeds. Inbound
  newsletter parsing is a planned collector; anything ingested must still pass
  through taxonomy triage so it remains matchable.
- **No automated tests**: the validation and parsing logic in `triage.py` and the
  matching logic are good candidates for a small pytest suite.

---

## 13. Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Source register, feed verification, decision log | Done |
| 2 | Collectors, SQLite, dedup, health checks, daily Action | Done |
| 3 | AI triage, taxonomy, scoring, Notion review, overrides | Done |
| 4 | Client matching (register, profiles, deterministic engine) | Done |
| 5 | Distribution (per-client digests, urgent alerts) | Next |
| 6 | White-label, per-client branded delivery (e.g. email) | Planned |

`docs/ROADMAP.md` holds the detailed checklist and current status.

---

## 14. Working model

- Planning, decisions, and document deliverables: Claude (claude.ai, project
  workspace).
- Build and code: Claude Code, using `CLAUDE.md` and `docs/` as context.
- All locked choices are recorded in `docs/DECISIONS.md` before build. Propose
  changes to decided items as new decision entries, not by re-litigating.
