# Phase 3 Build Spec: Triage

Status: Approved design, 2026-07-09. Build target for Claude Code.
Governing decisions: D-008, D-015, D-016, D-017, D-018.
Read CLAUDE.md first. Do not re-litigate decided items.

## Scope

Four deliverables, built in this order:

1. Schema migration: triage columns and overrides table
2. Triage script: `src/triage.py`
3. Notion sync: `src/notion_sync.py` (push) and sync-back with override logging
4. Secrets and cost logging

Out of scope: batch API, prompt caching, KEV pre-filter (D-015), automatic
triggering, digest generation (Phase 4).

## 1. Schema migration

Add to the `items` table (never alter existing columns or rows):

- `triaged_at` TEXT (ISO 8601 UTC, null until triaged)
- `auto_discard` TEXT (null, 'AD-2', or 'AD-3')
- `theme_tags` TEXT (JSON array of strings)
- `sector_tags` TEXT (JSON array of strings)
- `jurisdiction` TEXT
- `type` TEXT
- `level` TEXT ('Urgent', 'High', 'Standard', 'Low', or null if discarded)
- `rules_applied` TEXT (JSON array of strings)
- `ai_summary` TEXT (do not reuse the existing `summary` column, which
  holds the feed snippet)
- `flagged` INTEGER (0 or 1)
- `flag_rules` TEXT (JSON array of strings)
- `flag_reason` TEXT
- `confidence` TEXT ('high', 'medium', 'low')
- `fetch_status` TEXT ('ok', or a short failure reason such as 'http_403',
  'timeout', 'empty_content')
- `model` TEXT (model string used, for the audit trail)
- `input_tokens` INTEGER, `output_tokens` INTEGER (per item, from the API
  response usage block)
- `review_status` TEXT (default 'New'; values New, Reviewed, Published,
  Discarded, mirrored from Notion by sync-back)
- `notion_page_id` TEXT (set on first push to Notion)

New table `overrides`:

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `item_id` INTEGER NOT NULL (references items.id)
- `original_level` TEXT NOT NULL
- `final_level` TEXT NOT NULL
- `reason` TEXT
- `recorded_at` TEXT NOT NULL (ISO 8601 UTC)

Migration must be idempotent (safe to run twice). Use ALTER TABLE ADD
COLUMN guarded by a check of existing columns.

## 2. Triage script (src/triage.py)

Run manually: `python -m src.triage`. No scheduler changes in this phase.

Eligibility query (D-017):

    SELECT ... FROM items
    WHERE triaged_at IS NULL
    AND (source != 'CISA_KEV' OR retrieved_at >= '2026-07-08T00:00:00')

Note: retrieved_at values carry a +00:00 offset suffix. String comparison
with the prefix above is correct for this data, but verify against actual
stored values before relying on it.

Per item:

1. Fetch the item URL with `requests` (timeout 20s, a plain descriptive
   User-Agent). Extract readable text with BeautifulSoup (strip nav,
   script, style). Cap at FETCH_CHAR_CAP = 20000 characters. On any
   failure, set fetch_status to the failure reason and proceed with
   feed_snippet only per D-016. Never skip the item.
2. Load `src/triage_prompt.md`, strip the header block above the `---`
   separator, fill the placeholders. {{TAXONOMY_V1_0}} and
   {{SCORING_CRITERIA_V1_0}} are the full runtime-read contents of
   `docs/taxonomy-v1.0.md` and `docs/scoring-criteria.md`.
3. Call the Claude API, model `claude-sonnet-4-6`, max_tokens 1500,
   temperature 0. Single user message. No system prompt needed beyond
   the template.
4. Parse the JSON response. Validate before writing:
   - every tag string must exist verbatim in the taxonomy document
   - level must be one of the four levels or null
   - cardinality: 1 to 3 themes, 0 to 2 sectors, exactly 1 jurisdiction,
     exactly 1 type
   If validation fails, retry once with the validation error appended to
   the prompt. If it fails again, mark the item flagged with
   flag_reason 'invalid model output' and store the raw response in
   flag_reason for inspection. Do not invent values.
5. Write results plus model, input_tokens, output_tokens, triaged_at.
   Commit per item so a crash loses at most one item's work.

Run report, printed at the end and appended to `logs/triage_runs.jsonl`
(one JSON line per run): run timestamp, items eligible, items triaged,
items flagged, items discarded, fetch failures, total input tokens, total
output tokens, cost in USD computed at $3.00 per million input and $15.00
per million output tokens. Pricing constants live at the top of the
script with a dated comment, verified 2026-07-09.

## 3. Notion sync

Push (`python -m src.notion_sync push`):

- Creates the database if `NOTION_DATABASE_ID` is unset: print
  instructions instead of creating silently; the parent page must be
  chosen by the owner.
- One page per item where triaged_at is set and notion_page_id is null.
  Properties per D-018: Title, URL, Source, Published date, Level,
  AI Level, Themes, Sectors, Jurisdiction, Type, Status (default New),
  Flagged, Flag reason, Summary, Confidence, Override reason (empty),
  item_id.
- Level and AI Level are both set to the model's level on first push.
  AI Level is never written again.
- Store notion_page_id back in SQLite.

Sync-back (`python -m src.notion_sync pull`):

- For every item with a notion_page_id: read Status, Level, Override
  reason.
- Write Status to items.review_status.
- If Level differs from AI Level and no override row exists yet for that
  item and final level, insert into `overrides` (original_level = AI
  Level, final_level = Level, reason = Override reason). If Override
  reason is empty, still log the override and print a warning listing
  the items missing a reason.
- Notion writes nothing else back. SQLite is the system of record
  (D-008); raw and triage columns are never modified by sync-back.

Rate limits: the Notion API allows roughly 3 requests per second.
Sleep 350ms between requests. Volume is tiny; do not build batching.

## 4. Secrets and cost

- Local: `ANTHROPIC_API_KEY`, `NOTION_API_KEY`, `NOTION_DATABASE_ID` in
  `.env`, loaded with python-dotenv. `.env` is already gitignored;
  verify before first commit.
- Add `.env.example` with the three variable names and no values.
- GitHub Actions: same names as repo secrets, for the later
  workflow_dispatch trigger. Do not build the workflow in this phase.
- Cost logging per run is defined in section 2 and is mandatory from
  run one.

## Dependencies

anthropic, notion-client, python-dotenv added to requirements. Keep
feedparser, requests, beautifulsoup4 as is. Nothing else.

## Acceptance checklist

- [ ] Migration runs twice without error; raw columns and rows untouched
- [ ] Triage run on the eligible set (roughly 36 items) completes; every
      item gets either results or a flagged failure state; none skipped
- [ ] All tags in the database exist verbatim in taxonomy-v1.0.md
- [ ] Run report shows tokens and USD cost; logs/triage_runs.jsonl written
- [ ] KEV items retrieved before 2026-07-08 remain untriaged
- [ ] Notion board populated; Status edits and a test Level override sync
      back; override row created with original and final level
- [ ] No secrets in the repo (search history for key patterns before push)

## Operator workflow (for the owner, after build)

1. `git pull` (the Actions bot commits daily; always pull first)
2. `python -m src.triage`
3. `python -m src.notion_sync push`
4. Review in Notion: set Status, adjust Level where wrong, give a reason
5. `python -m src.notion_sync pull`
6. `git add finalogic.db logs/ && git commit -m "Triage run" && git push`
