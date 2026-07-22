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

Wave 2 expansion (Phase 6, D-029), added as each feed is verified:

| Source | Type | Feed |
|--------|------|------|
| EIOPA | RSS | European Insurance and Occupational Pensions Authority news |
| EC_DIGITAL | RSS | European Commission, Shaping Europe's Digital Future (AI Act and digital policy) |
| EDPB | RSS | European Data Protection Board |
| NCSC_UK | RSS | UK National Cyber Security Centre news and alerts |
| ECB_SSM | RSS | ECB banking supervision (SSM) press releases and speeches |

Health checks make zero-item runs visible and fail the job, so a silently broken
feed is caught rather than passing as a quiet no-op.

### Stage 2: Triage (`src/triage.py`, `src/llm.py`)

One model call per untriaged item. The stage **fetches the article**, not just the
title: it downloads the item's URL, strips scripts, navigation, headers and
footers, caps the text at 20,000 characters, and puts that page text into the
prompt alongside the title and the feed snippet. If the fetch fails (403,
timeout, cookie wall) triage proceeds on title and snippet alone **and flags
F-3**, so a thin read can never be mistaken for a full one. Items are never
silently skipped.

The prompt is `src/triage_prompt.md`, with the taxonomy and scoring criteria
injected verbatim at runtime, so the locked documents stay the single source of
truth and version drift is impossible.

The response is validated before anything is written:

- Tags must come from the locked taxonomy (theme, sector, jurisdiction, type).
- Level must be one of Urgent / High / Standard / Low, or null when discarded.
- `rules_applied` must be bare level, weighting, or discard rule IDs. Flag rules
  (F-1 to F-4) are validated separately, in `flag_rules` (D-021).
- On a validation failure the stage retries once, carrying the error back to the
  model. On a second failure the item is flagged as "invalid model output" and
  no tags, level, or summary are written. Nothing is invented.

**The model is a replaceable component (D-026).** All model-aware code lives in
`src/llm.py`, roughly a hundred lines wrapping one HTTP call. The prompt, the
locked documents, and the validator do not know which model answered. The
provider is kie.ai and the model is set by `KIE_MODEL` in the environment, not in
code. `items.model` records what produced each row, so provenance survives a
provider change.

Raw collection columns are never altered by triage. Two logs are written:

| Log | What it answers |
|-----|-----------------|
| `logs/triage_runs.jsonl` | Did the run work? Counts, tokens, cost, per run. |
| `logs/triage_items.jsonl` | What was decided, about which document? One line per item, **with the source URL**, so any tag, level, or summary can be checked against the published page that produced it. |

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

### Stage 5: Distribute (`src/distribute/`)

Each client gets a Markdown digest of the matches not yet sent to them, grouped
by level, showing the summary triage wrote and the reason the item matched. No
model is called: the digest reuses `ai_summary`, which a human has already seen
and approved.

Channels are output plugins, symmetric with collectors on the intake side: one
per destination behind a `deliver` interface, selected in
`config/distribution.yaml`. `file` and `console` are built; email is deferred to
Phase 7 (D-024).

`delivered_at` is the idempotency key. It is stamped only after a channel reports
success, so a delivered match is never re-sent and a failed send is retried on
the next run. Distribution also re-checks the human gate at send time, because a
reviewer can move an item back to New or Discarded after it was matched.

### The orchestrator (`src/pipeline.py`)

Runs the whole cycle in order: collect, triage, push, pull, match, distribute. It
stops at the first failure, because each stage consumes the output of the one
before it. `--dry-run` previews everything and writes, sends, and charges nothing.

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
β”β”€β”€ README.md                     # this file
β”β”€β”€ CLAUDE.md                     # working context for Claude Code sessions
β”β”€β”€ requirements.txt
β”β”€β”€ .env.example                  # copy to .env; secrets go here (gitignored)
β”β”€β”€ finalogic.db                  # SQLite system of record (committed, D-008)
β”β”€β”€ .github/workflows/collect.yml # daily collection on GitHub Actions
β”β”€β”€ config/
β”‚   β”β”€β”€ clients.yaml              # client register (interest profiles)
β”‚   β””β”€β”€ distribution.yaml         # which channel digests are delivered on
β”β”€β”€ data/                         # delivered digests (gitignored, D-024)
β”β”€β”€ docs/
β”‚   β”β”€β”€ DECISIONS.md              # decision log (D-001..; locked choices)
β”‚   β”β”€β”€ ROADMAP.md                # phased build plan and status
β”‚   β”β”€β”€ taxonomy-v1.0.md          # controlled tag vocabulary (locked)
β”‚   β”β”€β”€ scoring-criteria.md       # relevance and urgency rules (locked)
β”‚   β”β”€β”€ finalogic-source-register.md
β”‚   β”β”€β”€ feed-verification.md
β”‚   β””β”€β”€ phase3-*.md, phase5-*.md
β”β”€β”€ logs/
β”‚   β”β”€β”€ triage_runs.jsonl         # per-run counts, tokens, cost
β”‚   β”β”€β”€ triage_items.jsonl        # per-item decisions WITH the source URL (audit trail)
β”‚   β””β”€β”€ demo_items.jsonl          # demo output only (gitignored, truncated each run)
β”β”€β”€ tests/                        # pytest: run `pytest` from the repo root
β”‚   β”β”€β”€ conftest.py               # temporary database, never finalogic.db
β”‚   β”β”€β”€ test_matching.py          # the matching rule: overlap, level gate, scoring
β”‚   β”β”€β”€ test_triage_validation.py # model output validation
β”‚   β”β”€β”€ test_taxonomy.py          # the taxonomy parser
β”‚   β””β”€β”€ test_distribution.py      # the human gate and the idempotency guard
β””β”€β”€ src/
    β”β”€β”€ db.py                     # SQLite schema and item insert
    β”β”€β”€ migrate.py                # additive triage-column migration
    β”β”€β”€ sources.py                # verified feed URLs
    β”β”€β”€ llm.py                    # THE ONLY model-aware code. Swap providers here.
    β”β”€β”€ pipeline.py               # full-cycle orchestrator, with --dry-run
    β”β”€β”€ demo.py                   # one-command live demo of the whole cycle
    β”β”€β”€ collectors/               # INTAKE plugins, one per source
    β”‚   β”β”€β”€ base.py               # shared RSS fetch, logging, timestamps
    β”‚   β””β”€β”€ eba.py, esma.py, cert_eu.py, cisa_kev.py,
    β”‚       eiopa.py, ec_digital.py, edpb.py,
    │       ncsc_uk.py, ecb_ssm.py
    β”β”€β”€ run.py                    # run all collectors, report health
    β”β”€β”€ triage.py                 # AI triage, validation, run log
    β”β”€β”€ triage_prompt.md          # approved prompt template
    β”β”€β”€ notion_sync.py            # Notion push and pull, override logging
    β”β”€β”€ clients.py                # client register seeding and validation
    β”β”€β”€ matching.py               # deterministic client matching engine
    β””β”€β”€ distribute/               # OUTPUT plugins, one per channel
        β”β”€β”€ digest.py             # per-client Markdown digest from the ledger
        β””β”€β”€ channels.py           # file, console (email deferred to Phase 7)
```

The shape is symmetric. `collectors/` are intake plugins, `distribute/` are
output plugins, and the deterministic core sits between them.

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

1. **Overlap**: the item shares at least one **sector or theme** with the client
   profile. Jurisdiction alone is not enough (D-028): nearly every item and
   client is EU, so matching on jurisdiction by itself routed every EU item to
   every EU client. A shared jurisdiction still boosts the score and is named in
   the match reason when a real sector or theme overlap exists.
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

Weights are constants at the top of `src/matching.py`. Jurisdiction keeps the
highest weight because it still routes same-jurisdiction items more strongly and
will prioritise Cyprus items once the Cyprus sources land; it just no longer
matches on its own.

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

Dependencies: `feedparser`, `requests`, `beautifulsoup4`, `notion-client`,
`python-dotenv`, `pyyaml`, and `pytest` for the tests. There is no vendor SDK for
the model: it is one HTTP call.

### Configure secrets

Copy `.env.example` to `.env` and fill in. `.env` is gitignored and must never be
committed. In GitHub Actions these are repository secrets with the same names.

```
KIE_API_KEY=            # triage provider (kie.ai). Required.
KIE_BASE_URL=https://api.kie.ai
KIE_MODEL=gemini-3-5-flash    # swap the model here, not in code
KIE_THINKING_LEVEL=low        # low (cheap) or high

NOTION_API_KEY=         # the human review board
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
python -m src.triage                     # add --limit N to bound a run
python -m src.triage --dry-run           # build prompts, no API calls, no writes
python -m src.triage --source EIOPA --limit 3   # shake down one source (repeatable flag)

# 3. Human review
python -m src.notion_sync push           # create pages for newly triaged items
#    ... reviewers set Status and Level in Notion ...
python -m src.notion_sync pull           # read Status/Level back, log overrides

# 4. Seed clients (once, and whenever config/clients.yaml changes)
python -m src.clients seed

# 5. Match approved items to clients
python -m src.matching run
python -m src.matching report

# 6. Distribute: build and send the per-client digests
python -m src.distribute.digest --client "Bank (example)"   # preview, writes nothing
python -m src.distribute.digest --all                       # preview every client
python -m src.distribute.digest --all --send                # deliver and mark delivered
python -m src.distribute.digest --all --send --channel console
```

Matching should run after `notion_sync pull`, since the pull is what sets
`review_status`. Use `python -m src.matching preview` at any time to see how
matching would behave over the full triaged backlog.

Distribution sends nothing without `--send`. Without it you get the digest on
stdout and nothing is marked delivered. With it, each client's digest goes to the
channel named in `config/distribution.yaml` and those matches are stamped
`delivered_at`, so the next run sends nothing.

### The whole cycle at once

```bash
python -m src.pipeline --dry-run              # preview everything; no writes, no cost
python -m src.pipeline                        # collect, push, pull, match
python -m src.pipeline --triage --distribute  # the full cycle
python -m src.pipeline --only match distribute
python -m src.pipeline --skip collect
```

`triage` and `distribute` are opt-in on a live run: one spends money, the other
sends things. A dry run previews both for free. The pipeline stops at the first
failing stage rather than running on partial data.

### See it work, in one command

```bash
python -m src.demo
```

Runs the whole cycle live and narrates each stage: fetches the four real source
websites, triages fresh items (showing the page text it actually read, the rule
that justified the level, and what each item cost), demonstrates the human gate
blocking unreviewed items, approves one, matches it to clients, prints the
digest, then re-runs distribution to show nothing is ever sent twice.

Costs a few cents. It works on a **copy** of the database and never writes to
`finalogic.db`, so it is safe to run repeatedly in front of anyone. It rewinds
the copy's triage state for the most recent real publications, so it keeps
working after the backlog is cleared, and it presents on a fixed date so its
output is reproducible.

| Flag | Effect |
|------|--------|
| `--limit N` | how many items to triage (default 3, about $0.002 each) |
| `--date YYYY-MM-DD` | the date the demo presents as running on |
| `--no-collect` | skip the live fetch, use what is already stored |
| `--no-rewind` | triage only genuinely untriaged items (drains the backlog) |

The two things it fakes are stated on screen: it works on a copy, and it stands
in for the Notion reviewer by approving one item directly, because a demo cannot
wait for a human. Everything else is real.

### Tests

```bash
pytest
```

Covers the matching rule, triage output validation, the taxonomy parser, and the
human gate plus the idempotency guard. Tests build a temporary database from the
real schema code and never touch `finalogic.db`.

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
- **Model and cost**: triage runs `gemini-3-5-flash` via kie.ai (D-026), at about
  **$0.002 per item, roughly $4.50 a year** at 6 items a day. Change the model by
  setting `KIE_MODEL`, not by editing code. The pricing constants in
  `src/triage.py` are marked TBD: verify them against your kie.ai billing before
  trusting the cost figures in `logs/triage_runs.jsonl`. A wrong constant
  misreports cost and cannot affect triage output.
- **Where the tokens go**: roughly 85% of every prompt is the taxonomy and the
  scoring criteria, re-sent on every call. That is the cost of having one source
  of truth (D-016) and is not worth optimising at this volume. If volume grows
  sharply, prompt caching is the lever, not fetching less and not the model.
- **Watch the flag rate**: the Claude runs flagged 13 of 36 items. Under-flagging
  is the dangerous failure with a cheaper model, because it does not look like an
  error, it looks like confidence, and it pushes items past the human gate
  unexamined. If the flag rate drops materially on comparable items, set
  `KIE_THINKING_LEVEL=high` or move to a stronger model slug (see D-026).
- **Console encoding**: the client tooling forces UTF-8 stdout so item titles
  with non-ASCII characters (Greek from Cyprus sources, zero-width spaces from
  EBA) print without crashing on a legacy Windows console.

---

## 12. Known limitations and next steps

- **Database in git**: `finalogic.db` is committed and rewritten by the daily
  Action. Decided for the PoC (D-025, 2026-07-16): it stays in git, with the
  workflow serialised by a concurrency group and a pre-push rebase so runs
  cannot race. The git history still bloats with a daily binary blob; before a
  client-facing launch the file should move to hosted SQLite (Turso or
  Litestream). D-008 is unchanged: SQLite remains the system of record.
- **The clients are examples**: every entry in `config/clients.yaml` is a
  placeholder. Nothing can reach a real recipient until they are replaced, which
  is deliberate.
- **No email channel**: `file` and `console` are built. SendGrid is the locked
  stack (D-003) but delivery to a real address is Phase 7 (D-024).
- **Urgent items wait for the digest**: there is no separate immediate alert path
  yet. The channel interface is the hook for one.
- **Newsletter ingestion**: current collectors are RSS and JSON feeds. Inbound
  newsletter parsing is a planned collector; anything ingested must still pass
  through taxonomy triage so it remains matchable.

---

## 13. Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Source register, feed verification, decision log | Done |
| 2 | Collectors, SQLite, dedup, health checks, daily Action | Done |
| 3 | AI triage, taxonomy, scoring, Notion review, overrides | Done |
| 4 | Client matching (register, profiles, deterministic engine) | Done |
| 5 | Distribution (digests, channels, orchestrator, tests) | Done |
| 6 | Coverage expansion (Wave 2 scrapers plus four RSS additions, D-029; threshold tuning) | In progress |
| 7 | White-label (email via SendGrid, branded templates) | Planned |

Phases were renumbered on 2026-07-14 (D-023): distribution took Phase 5, so
coverage expansion moved to 6 and white-label to 7. Decisions D-015, D-018, and
D-020 predate this and say "Phase 5" where they mean coverage expansion.

`docs/ROADMAP.md` holds the detailed checklist and current status.

---

## 14. Working model

- Planning, decisions, and document deliverables: Claude (claude.ai, project
  workspace).
- Build and code: Claude Code, using `CLAUDE.md` and `docs/` as context.
- All locked choices are recorded in `docs/DECISIONS.md` before build. Propose
  changes to decided items as new decision entries, not by re-litigating.
