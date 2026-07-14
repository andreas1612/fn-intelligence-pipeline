# Phase 5 build session prompt (paste into Claude Code)

Saved 2026-07-14. Paste the text below the line into a fresh Claude Code
session opened in the project root.

Context for the owner: Phase 4 (client matching) is built and pushed. The
repository now lives at https://github.com/andreas1612/fn-intelligence-pipeline.
Phase 5 is distribution: getting matched intelligence to the client.

---

You are building Phase 5 (Distribution) of the Finalogic intelligence
pipeline. The pipeline already collects, triages, human-reviews, and matches
items to clients. Your job is to close the last mile: deliver each client the
intelligence matched to them, and record what was sent.

Read in this order before writing any code:

1. README.md (full architecture, data model, and how each stage runs)
2. CLAUDE.md (project brief and hard rules)
3. docs/DECISIONS.md (locked choices, do not re-litigate)
4. src/matching.py and src/clients.py (the matching layer you build on,
   and the conventions to match)
5. src/notion_sync.py (existing delivery-adjacent conventions)
6. docs/taxonomy-v1.0.md and docs/scoring-criteria.md (the controlled
   vocabulary, read only, never copy into code)

## What Phase 5 must deliver

Build these in order. Complete and show me each one before starting the next.

1. **src/distribute/digest.py**: build a per-client digest from the matches
   ledger. For one client, gather every match where `delivered_at IS NULL`,
   join to the item, group by level (Urgent, High, Standard, Low), and render
   Markdown. Each entry shows title, source, level, the item's `ai_summary`,
   the URL, and the `matched_on` reason. Reuse the summary triage already
   produced. Do not make a new model call.

2. **src/distribute/channels.py**: pluggable delivery channels behind one
   interface, mirroring how `collectors/` works for intake. Build `file`
   (write `data/digests/<client>/<date>.md`) and `console` now. Add `email`
   only if I approve the dependency first. Channel selection is configuration,
   not code changes at the call site.

3. **Mark delivered**: after a channel reports success, set
   `matches.delivered_at`. This is the idempotency key. A delivered match is
   never sent again. A failed send leaves `delivered_at` null so the next run
   retries it.

4. **src/pipeline.py**: one orchestrator that runs the full cycle in order:
   collect, triage, Notion push, Notion pull, match, distribute. Flags to skip
   stages and a `--dry-run` that previews without writing or sending.

5. **Tests (tests/, pytest)**: cover the matching rule (overlap, level gate,
   scoring), the triage output validation, and the taxonomy parser. These are
   the three places where a silent regression would be most damaging.

6. **Decision entries in docs/DECISIONS.md**: D-023 records the client
   matching design retrospectively (profiles from the locked taxonomy,
   deterministic overlap plus level gate, human gate enforced). D-024 records
   the distribution design you build here.

## Ground rules for this session

- **The human gate is absolute.** Distribution sends only matches whose item
  has `review_status` in ('Reviewed', 'Published'). Never send an untriaged,
  discarded, or unreviewed item. Matching already enforces this; distribution
  must not widen it.
- **Never re-send.** `delivered_at` is the guard. Re-running distribution must
  be safe and produce nothing new.
- **No model calls in distribution.** The digest reuses `ai_summary` from
  triage. Summaries derive only from fetched text (hard rule 2). Adding an
  LLM-written executive summary is a separate decision, not this session.
- **Do not modify** collectors, `triage.py`, `db.py` raw columns, the taxonomy
  or scoring documents, or `.github/workflows/collect.yml`.
- **Schema changes are additive only.** Never drop or alter an existing column
  or row. Follow the `migrate.py` pattern.
- **Dependencies**: nothing new without asking. Email delivery would need
  SendGrid; propose it and wait for approval.
- **Style**: Python 3.11+, type hints, small single-purpose modules,
  parameterised SQL (`?`), short sentences in docs, no em dash character, TBD
  for anything uncertain.
- **Do not send anything to a real client or a real email address** without
  asking me first. Test with the file and console channels.
- If a requirement is ambiguous or conflicts with reality, stop and ask. Flag
  judgement calls explicitly. Do not resolve them silently.

## Target src/ structure after this phase

The shape is symmetric: `collectors/` are intake plugins, `distribute/` are
output plugins, and the deterministic core sits between them.

```
src/
    __init__.py
    db.py                  # SQLite connection, items schema, dedup insert
    migrate.py             # additive schema migration
    sources.py             # verified feed URLs (single source of truth)
    run.py                 # run all collectors, health checks
    pipeline.py            # NEW: full-cycle orchestrator
    triage.py              # AI triage and output validation
    triage_prompt.md       # approved prompt template
    notion_sync.py         # human review push and pull
    clients.py             # client register (seed and validate profiles)
    matching.py            # deterministic matching engine and ledger
    collectors/            # INTAKE plugins, one per source
        __init__.py
        base.py            # shared RSS fetch, logging, timestamps
        eba.py
        esma.py
        cert_eu.py
        cisa_kev.py
        cysec.py           # LATER (Wave 2, first scraper). Not this session.
    distribute/            # NEW: OUTPUT plugins, one per channel
        __init__.py
        digest.py          # build a per-client Markdown digest from matches
        channels.py        # file, console. email only if approved.
tests/                     # NEW: top level, not inside src
    test_matching.py
    test_triage_validation.py
    test_taxonomy.py
```

Do not create `cysec.py` in this session. It is Wave 2 and needs the live
CySEC page verified first.

## Acceptance checklist

Finish by reporting the status of each line:

- [ ] `python -m src.distribute.digest --client "<name>"` renders a digest of
      that client's undelivered matches, grouped by level, with reasons.
- [ ] A `file` channel writes the digest and sets `delivered_at`.
- [ ] Re-running distribution immediately after sends nothing (idempotent).
- [ ] An unreviewed or discarded item never appears in any digest.
- [ ] `python -m src.pipeline --dry-run` previews the full cycle with no writes.
- [ ] `pytest` passes, covering matching, triage validation, and the taxonomy
      parser.
- [ ] D-023 and D-024 are written in docs/DECISIONS.md.
- [ ] README.md is updated with the distribution stage and the new commands.

## Owner context

I have limited git experience. When git steps are needed, give exact commands
with a plain-language explanation. Remind me to `git pull` before local work,
because the Actions bot commits `finalogic.db` to the same branch.

Known structural issue, do not fix in this session: `finalogic.db` is a SQLite
file committed to git and rewritten by the daily Action. It cannot be diffed or
merged, and concurrent runs can race on push. Moving it to a hosted database is
the next infrastructure decision (proposed D-025). Flag it if it blocks you, but
do not migrate it here.
