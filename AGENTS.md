# AGENTS.md: Working context for Codex

## What this project is

A regulatory and cybersecurity intelligence pipeline for Finalogic Ltd, a Cyprus-based information security and regulatory advisory firm serving EMIs, fintechs, investment firms, and other regulated clients. EU and Cyprus financial-sector focus. AI regulation and AI security are priority themes.

Read `README.md` for architecture, then `docs/DECISIONS.md` for locked choices, then `docs/ROADMAP.md` for current phase and status. Do not re-litigate decided items; propose changes as new entries in DECISIONS.md instead.

## Hard rules

1. **Traceability**: Every item in the system must trace to a named source URL from the source register. No open web browsing, no discovered sources, no generated items.
2. **AI assists, humans decide**: The triage model classifies, scores, and summarises only text the pipeline provides. Summaries derive strictly from fetched content. Nothing is distributed without passing the human review gate in Notion. The model is a replaceable component (D-026): it lives behind `src/llm.py`, and the prompt, taxonomy, scoring rules, and validator are all model-agnostic.
3. **Controlled taxonomy and scoring**: Tag only from `docs/taxonomy-v1.0.md`. Score only per `docs/scoring-criteria.md`. No ad hoc tags or levels. This is enforced by the validator, not by trusting the model.
4. **Simple and boring wins**: Standard library and minimal dependencies (feedparser, requests, BeautifulSoup, notion sdk, pyyaml). No orchestration frameworks. No agents. No vendor SDK for the model: it is one HTTP call.
5. **SQLite is the system of record**: One database file, committed to the repo after each collection run. Notion is a view for human review, not the source of truth.
6. **PoC scope governs**: Build only the Wave 1 and Wave 2 sources defined at the top of `docs/finalogic-source-register.md`. Everything else is Phase 6 (coverage expansion) backlog.

## Conventions

- Python 3.11+, type hints, small single-purpose modules under `src/`
- Configuration in version-controlled files, secrets via GitHub Actions secrets only
- Every collector logs items retrieved per run; zero-item runs must be visible (health check requirement)
- Content hash (SHA-256 of normalised title + URL) for deduplication
- Feed URLs must be verified against the live site before a collector is coded; the register asserts no exact URLs
- Documentation style: short sentences, no em dash character, "TBD" for anything uncertain, no invented facts

## Current status

Phases 1 to 5 complete: foundations, Wave 1 collectors, AI triage with the Notion
review board, client matching, and distribution (per-client digest, file and console
channels, full-cycle orchestrator, first test suite).

Next: Phase 6, coverage expansion (Wave 2 sources, starting with the CySEC scraper).

Phase numbering changed on 2026-07-14 (D-023). Distribution was built as Phase 5 and
coverage expansion moved to Phase 6. Decisions D-015, D-018, and D-020 predate this
and use "Phase 5" to mean coverage expansion and threshold tuning; read those as
Phase 6. See `docs/ROADMAP.md` for the authoritative phase list.
