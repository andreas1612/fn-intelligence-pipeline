# Finalogic Intelligence Pipeline

Structured regulatory and cybersecurity intelligence pipeline for Finalogic Ltd.

## Purpose

Monitor high-quality official sources continuously, triage with AI assistance, review with human judgement, and distribute structured intelligence. Internal use first. Designed from day one to support a white-labelled, client-facing service.

## Architecture (agreed)

Three-layer deterministic pipeline with a human gate:

1. **Collect**: Python scripts poll a fixed, versioned source register (RSS via feedparser, scrapers via BeautifulSoup for non-RSS sources). Every item stores source name, URL, publication date, retrieval timestamp, and content hash.
2. **Triage**: Claude API classifies each item against the controlled tag taxonomy, scores relevance against written criteria, and produces a summary derived only from fetched text. Structured JSON output. Low confidence items flagged for review.
3. **Distribute**: Weekly internal digest plus urgent alerts. Later: branded per-client emails via SendGrid with tag-based filtering.

Human review (Notion status gate) sits between Triage and Distribute. Nothing is published without it.

## Stack

- Python, run on schedule via GitHub Actions
- SQLite as system of record (committed to this private repo)
- Notion as human review and workspace layer
- Claude API for triage
- SendGrid for distribution (Phase 4+)
- Hosted in the Finalogic company GitHub organisation

## Repository layout

- `README.md`: this file
- `CLAUDE.md`: working context for Claude Code sessions
- `docs/DECISIONS.md`: decision log (locked choices and rationale)
- `docs/ROADMAP.md`: phased build plan and current status
- `docs/taxonomy-v1.0-draft.md`: tag taxonomy (draft, pending approval)
- `docs/scoring-criteria.md`: relevance and urgency scoring rules (TBD, in progress)
- `docs/source-register.md`: source register (to be added, see DECISIONS.md)
- `src/`: pipeline code (Phase 2 onwards)

## Working model

- Planning, decisions, and document deliverables: Claude (claude.ai, project workspace)
- Build and code: Claude Code, using CLAUDE.md and docs/ as context
- All decisions are recorded in docs/DECISIONS.md before build
