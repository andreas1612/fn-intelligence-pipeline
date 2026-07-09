# Roadmap and Status

Last updated: 2026-07-09

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

## Phase 3: Triage [NEXT]

Design approved 2026-07-09 (D-016 to D-018). Build spec: `docs/phase3-build-spec.md`. Approved prompt: `src/triage_prompt.md`.

- [ ] Triage prompt built from taxonomy v1.0 and scoring criteria v1.0 (verbatim rules)
- [ ] Claude API integration, structured JSON output, confidence flagging (F-1 to F-4)
- [ ] Notion review board: New, Reviewed, Published, Discarded
- [ ] Sync of triaged items to Notion

## Phase 4: Internal delivery

- [ ] Weekly internal digest from reviewed items
- [ ] Urgent alert path (channel TBD), human-verified per scoring criteria section 10

## Phase 5: Coverage expansion

- [ ] PoC Wave 2: CySEC scraper, CBC scraper, European AI Office, EUR-Lex OJ, ENISA scraper (D-012)
- [ ] Remaining Tier 1 sources onboarded per register priority
- [ ] Tier 2 sources onboarded selectively
- [ ] Scoring thresholds tuned from override log

## Phase 6: White-label

- [ ] SendGrid branded templates
- [ ] Per-client tag-based filtering
- [ ] Subscribe and unsubscribe management (SendGrid suppression groups)

## Rules

- A phase starts only when the previous phase's checklist is complete or explicitly waived in DECISIONS.md.
- Wave 2 may begin as soon as Wave 1 is stable; it does not wait for Phases 3 and 4 if capacity allows.
