# Phase 3 build session prompt (paste into Claude Code)

Saved 2026-07-09. Paste the text below the line into a fresh Claude Code
session opened in the project root.

---

You are building Phase 3 (Triage) of the Finalogic intelligence pipeline.
Design is approved and locked. Your job is to implement it exactly, not to
redesign it.

Read in this order before writing any code:

1. CLAUDE.md (project brief and hard rules)
2. docs/phase3-build-spec.md (your build target, follow it exactly)
3. docs/DECISIONS.md, entries D-015 to D-018 (the decisions the spec
   implements)
4. src/triage_prompt.md (the approved prompt template, use verbatim,
   do not rewrite it)
5. src/db.py and src/run.py (existing conventions to match)

Ground rules for this session:

- Build the four deliverables in the spec order: schema migration, triage
  script, Notion sync, secrets and cost logging. Complete and show me each
  one before starting the next.
- Do not modify existing raw columns, existing collector code, or the
  collection workflow. Do not touch .github/workflows/collect.yml.
- Do not paste the taxonomy or scoring criteria into any file. The triage
  script reads docs/taxonomy-v1.0.md and docs/scoring-criteria.md at
  runtime and injects them into the prompt placeholders (D-016).
- Model: claude-sonnet-4-6, temperature 0, max_tokens 1500, one API call
  per item. No batch API, no prompt caching, no KEV pre-filter (D-015,
  D-016).
- Eligibility per D-017: untriaged items where source is not CISA_KEV, or
  retrieved_at >= 2026-07-08T00:00:00. Verify the comparison against real
  stored retrieved_at values before trusting it.
- Fetch failures never skip an item: proceed on title plus feed snippet,
  flag F-3, record fetch_status (D-016).
- Validate model output before writing: tags verbatim from the taxonomy,
  correct cardinality, valid level. Retry once with the validation error,
  then flag as 'invalid model output'. Never invent values.
- Cost logging from run one: per-item token counts in the items table,
  per-run report appended to logs/triage_runs.jsonl with USD cost at
  $3.00 per million input and $15.00 per million output tokens.
- Secrets via .env locally (ANTHROPIC_API_KEY, NOTION_API_KEY,
  NOTION_DATABASE_ID). Confirm .env is gitignored before anything else.
  Add .env.example with names only.
- Dependencies allowed: anthropic, notion-client, python-dotenv, plus the
  existing feedparser, requests, beautifulsoup4. Nothing else.
- Style: Python 3.11+, type hints, small single-purpose modules, short
  sentences in docs, no em dash character, TBD for anything uncertain.
- If the spec is ambiguous or conflicts with reality, stop and ask.
  Flag judgement calls explicitly. Do not resolve them silently.
- Finish by walking through the acceptance checklist at the end of the
  spec and reporting the status of each line. Do not run the real triage
  against the API without asking me first.

Owner context: I have limited git experience. When git steps are needed,
give exact commands with a plain-language explanation, and remind me to
git pull before local work because the Actions bot commits to the same
branch.
