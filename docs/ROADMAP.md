# Roadmap and Status

Last updated: 2026-07-22

## Phase numbering note (D-023)

The phases below were renumbered on 2026-07-14. Client matching became Phase 4 and
distribution became Phase 5, so coverage expansion moved from Phase 5 to Phase 6 and
white-label from Phase 6 to Phase 7. Decisions D-015, D-018, and D-020 were written
before this and say "Phase 5" where they mean coverage expansion and scoring threshold
tuning. Read those references as Phase 6. This list is authoritative.

## Phase 1: Foundations (documents, no code) [COMPLETE]

- [x] Architecture agreed and recorded (DECISIONS.md)
- [x] Workspace scaffolded
- [x] Tag taxonomy v1.0 approved (`taxonomy-v1.0.md`, locked 2026-07-07)
- [x] Scoring criteria v1.0 approved (`scoring-criteria.md`, locked 2026-07-07)
- [x] Source register filed and PoC scope defined (`finalogic-source-register.md` v1.1)

## Phase 2: Collect (PoC Wave 1) [COMPLETE]

Scope: the four Wave 1 sources in the source register (EBA, ESMA, CERT-EU, CISA KEV). RSS and API only. ENISA was in Wave 1 but moved to Wave 2 as a scraper per D-012 (feed discontinued).

- [x] Private repo created in Finalogic GitHub organisation, this workspace pushed (2026-07-08)
- [x] Feed URLs verified against live sites for all Wave 1 sources (see docs/feed-verification.md; ENISA feed found discontinued, see D-012)
- [x] SQLite schema (single items table) (`src/db.py`)
- [x] Collectors for Wave 1 sources (feedparser / API) (`src/collectors/`: eba, esma, cert_eu, cisa_kev)
- [x] Deduplication via content hash (`src/db.py:content_hash`, `UNIQUE` constraint, verified no duplicate hashes after two local runs)
- [x] Health check: items per source per run, zero-item alerting (`src/run.py`; logs items_fetched/items_new per source, non-zero exit on zero-item or failed collectors)
- [x] GitHub Actions workflow: scheduled runs, DB committed back to repo (`.github/workflows/collect.yml`; verified in CI 2026-07-08, github-actions[bot] committed finalogic.db after a manual run, write-back proven)

## Phase 3: Triage [COMPLETE]

Design approved 2026-07-09 (D-016 to D-018). Build spec: `docs/phase3-build-spec.md`. Approved prompt: `src/triage_prompt.md`.

- [x] Triage prompt built from taxonomy v1.0 and scoring criteria (verbatim rules, injected at runtime) (`src/triage_prompt.md`)
- [x] Model integration, structured JSON output, confidence flagging (F-1 to F-4) (`src/triage.py`; 36 items triaged on scoring v1.2, run log in `logs/triage_runs.jsonl`). Originally the Claude API; the provider moved to kie.ai on 2026-07-14 (D-026) and now lives behind `src/llm.py`. Everything above the model call is unchanged.
- [x] Notion review board: New, Reviewed, Published, Discarded (D-018)
- [x] Sync of triaged items to Notion, with sync-back of Status and Level and an override log (`src/notion_sync.py`; integrity guard per D-022)
- [x] Scoring criteria hardened from real review: v1.1 rule IDs (D-019), v1.2 U-1 flag (D-020), v1.3 provisional level (D-021)
- [x] Validator aligned with the prompt: F rules validated in flag_rules, not rules_applied (D-021 defect 2, closed 2026-07-14)

## Phase 4: Client matching [COMPLETE]

- [x] Client register and interest profiles, validated against the locked taxonomy (`config/clients.yaml`, `src/clients.py`)
- [x] Deterministic matching engine: tag overlap plus level gate, no AI (`src/matching.py`)
- [x] Match ledger with a `delivered_at` column reserved for distribution (D-023)
- [x] Human gate enforced: only Reviewed and Published items are matched

## Phase 5: Distribution [COMPLETE]

- [x] Per-client Markdown digest from undelivered matches, grouped by level, reusing the triage `ai_summary` and the `matched_on` reason. No model calls (`src/distribute/digest.py`)
- [x] Pluggable delivery channels, selected by configuration (`src/distribute/channels.py`, `config/distribution.yaml`; file and console built, email deferred)
- [x] `delivered_at` as the idempotency key: a delivered match is never re-sent, a failed send is retried next run
- [x] Full-cycle orchestrator with `--dry-run` (`src/pipeline.py`)
- [x] First test suite: matching rule, triage validation, taxonomy parser, human gate (`tests/`)
- [x] Design recorded (D-023, D-024)

## Phase 6: Coverage expansion [IN PROGRESS]

Scope expanded on 2026-07-20 (D-029): four RSS sources added and a build order set,
RSS before scrapers. See D-029 for the source list and rationale.

Done:

- [x] Database-in-git resolved before source volume grows (D-025: stays in git for the PoC, workflow serialised with a concurrency group and pre-push rebase)
- [x] Matching relevance tightened: a shared sector or theme is required, jurisdiction is a booster not a standalone match (D-028)

6a. RSS and API collectors first (low build risk, fast volume). Verify each feed live
before coding. [COMPLETE 2026-07-21] All five built, verified, and registered. Nine
sources now collect green in one run. Feed evidence, including the candidates that
were rejected and why, is in `docs/feed-verification.md`; the feed-scope choices are
D-030. A 15-item sample (3 per new source) was triaged: 0 invalid outputs, the
Insurance sector and International jurisdiction tags fired for the first time, and
D-028 held with zero jurisdiction-only matches.

- [x] EIOPA (RSS) - the third ESA; activates the Insurance sector tag (`src/collectors/eiopa.py`; feed verified 2026-07-21, 30 items on first run, dedup confirmed on re-run)
- [x] European Commission, AI / Shaping Europe's Digital Future (RSS) - AI regulation theme volume (`src/collectors/ec_digital.py`; feed verified 2026-07-21, site-wide feed, no AI-only feed exists, 10 items on first run, dedup confirmed)
- [x] EDPB (RSS) - Data protection and privacy theme (`src/collectors/edpb.py`; feed verified 2026-07-21, 10 items on first run, dedup confirmed)
- [x] NCSC UK (RSS) - cyber volume beyond CERT-EU and KEV; first International-jurisdiction source (`src/collectors/ncsc_uk.py`; feed verified 2026-07-21 from the NCSC feeds page, News feed chosen over All/Guidance/Report/Blog, 20 items on first run, dedup confirmed)
- [x] ECB / SSM (RSS) - prudential supervision, cyber resilience expectations (D-027) (`src/collectors/ecb_ssm.py`; feed verified 2026-07-21 from the SSM RSS index, supervision press feed not the monetary-policy-led main ECB feed, 15 items on first run, dedup confirmed)

6b. Scrapers (the Cyprus differentiator and the real build risk):

- [ ] CySEC scraper - first scraper
- [ ] CBC scraper
- [ ] ENISA scraper (RSS/API feed discontinued, D-012)

6c. Structured legal and AI sources:

- [ ] EUR-Lex / Official Journal (API or email alerts)
- [ ] European AI Office (RSS or scrape)

Then:

- [ ] Scoring thresholds tuned from the override log (the "Phase 5 tuning" of D-018 and D-020; needs a one-model re-triage first, per D-026 risk 3)
- [ ] Remaining Tier 1 and selected Tier 2 sources per register priority

Parked until Phase 6 volume exists (owner decision 2026-07-20, D-029):

- Client-relevant systems list (KEV noise filter and strict Urgent, scoring section 12)
- Type-based filtering in matching and client profiles
- Notion review views grouped by Type

## Phase 7: White-label

- [ ] Email channel via SendGrid (stack already locked by D-003; deferred out of Phase 5 by D-024)
- [ ] SendGrid branded templates
- [ ] Per-client tag-based filtering (the matching engine from Phase 4 is the basis)
- [ ] Subscribe and unsubscribe management (SendGrid suppression groups)
- [ ] Replace the example clients in `config/clients.yaml` with real ones

## Rules

- A phase starts only when the previous phase's checklist is complete or explicitly waived in DECISIONS.md.
- Wave 2 may begin as soon as Wave 1 is stable; it does not wait for Phases 3 and 4 if capacity allows.
