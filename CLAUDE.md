# CLAUDE.md: Working context for Claude Code

## What this project is

A regulatory and cybersecurity intelligence pipeline for Finalogic Ltd, a Cyprus-based information security and regulatory advisory firm serving EMIs, fintechs, investment firms, and other regulated clients. EU and Cyprus financial-sector focus. AI regulation and AI security are priority themes.

Read `README.md` for architecture, then `docs/DECISIONS.md` for locked choices, then `docs/ROADMAP.md` for current phase and status. Do not re-litigate decided items; propose changes as new entries in DECISIONS.md instead.

## Hard rules

1. **Traceability**: Every item in the system must trace to a named source URL from the source register. No open web browsing, no discovered sources, no generated items.
2. **AI assists, humans decide**: The Claude API classifies, scores, and summarises only text the pipeline provides. Summaries derive strictly from fetched content. Nothing is distributed without passing the human review gate in Notion.
3. **Controlled taxonomy and scoring**: Tag only from `docs/taxonomy-v1.0.md`. Score only per `docs/scoring-criteria.md`. No ad hoc tags or levels.
4. **Simple and boring wins**: Standard library and minimal dependencies (feedparser, requests, BeautifulSoup, anthropic, notion sdk). No orchestration frameworks. No agents.
5. **SQLite is the system of record**: One database file, committed to the repo after each collection run. Notion is a view for human review, not the source of truth.
6. **PoC scope governs**: Build only the Wave 1 and Wave 2 sources defined at the top of `docs/finalogic-source-register.md`. Everything else is Phase 5 backlog.

## Conventions

- Python 3.11+, type hints, small single-purpose modules under `src/`
- Configuration in version-controlled files, secrets via GitHub Actions secrets only
- Every collector logs items retrieved per run; zero-item runs must be visible (health check requirement)
- Content hash (SHA-256 of normalised title + URL) for deduplication
- Feed URLs must be verified against the live site before a collector is coded; the register asserts no exact URLs
- Documentation style: short sentences, no em dash character, "TBD" for anything uncertain, no invented facts

## Current status

Phase 1 complete. Phase 2 active: Wave 1 collectors (EBA, ESMA, ENISA, CERT-EU, CISA KEV), SQLite schema, dedup, health checks, GitHub Actions workflow. See `docs/ROADMAP.md` for the checklist.
