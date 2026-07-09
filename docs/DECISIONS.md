# Decision Log

Locked decisions with rationale. Propose changes as new dated entries, do not edit history.

## D-001: Overall approach (2026, pre-workspace)

**Decision**: Custom Python pipeline (Option A), not low-code (n8n, Power Automate), not commercial platforms, not agentic browsing.
**Rationale**: Full traceability and audit trail, version control, low running cost, white-label capability. Commercial platforms lack Cyprus source depth (CySEC, CBC) and white-label rights. Agentic browsing cannot guarantee named-source traceability, which is a red line.

## D-002: Architecture (2026, pre-workspace)

**Decision**: Three layers: Collect, Triage, Distribute, with a human review gate before distribution.
**Rationale**: Deterministic, auditable, predictable cost. AI used only where it outperforms rules (classification, summarisation), never for discovery or publication.

## D-003: Stack (2026, pre-workspace, refined 2026-07-07)

**Decision**: Python collectors (feedparser, BeautifulSoup), Claude API triage with structured JSON, Notion for human review, SendGrid for distribution, code in the Finalogic company GitHub organisation.
**Rationale**: Fewest moving parts, skills in-house, each component replaceable.

## D-004: DORA is a tag, not a source (2026, pre-workspace)

**Decision**: DORA content is captured via tagging across multiple publishers (EBA, ESMA, EIOPA, EUR-Lex, CySEC, CBC, ENISA, CERT-EU, ESAs Joint Committee), not as a single feed.
**Rationale**: DORA is a topic dimension. Its content is distributed across regulatory publishers.

## D-005: White-label built in from day one (2026, pre-workspace)

**Decision**: Per-client filtering and branded templates are design constraints from Phase 1, even though internal use comes first.
**Rationale**: Retrofitting client segmentation is costly. Tag-based filtering makes it nearly free if designed in early.

## D-006: Hosting and scheduling (2026-07-07)

**Decision**: GitHub Actions on a schedule, private repo in the Finalogic organisation.
**Rationale**: Free at this volume, no server to maintain, secrets management built in.

## D-007: Delivery cadence (2026-07-07)

**Decision**: Weekly internal digest plus an urgent alert path for critical items.
**Rationale**: Weekly matches review capacity. Urgent path requires an explicit "urgent" threshold in the scoring criteria (now U-1 to U-4).

## D-008: SQLite as system of record (2026-07-07)

**Decision**: Minimal SQLite database as the canonical store from day one, committed to the repo after each collection run. Notion is the human review layer only.
**Rationale**: Notion is weak as a database (rate limits, no querying, SaaS-held audit trail). Migrating later would mean lossy backfill through a rate-limited API. SQLite costs about ten lines of code now.

## D-009: Pipeline health monitoring from day one (2026-07-07)

**Decision**: Track items per source per week; alert on silent zero-item sources.
**Rationale**: Silently broken scrapers or feeds are the most likely real-world failure mode.

## D-010: PoC scope, two waves (2026-07-07)

**Decision**: The PoC ingests nine sources in two waves. Wave 1 (RSS/API only): EBA, ESMA, ENISA, CERT-EU, CISA KEV. Wave 2: CySEC (scrape), CBC (scrape), European AI Office, EUR-Lex OJ. All other register sources are Phase 5 backlog.
**Rationale**: Wave 1 is low build risk and exercises the full pipeline end to end. Wave 2 adds the Cyprus differentiator, the AI priority theme, and authoritative legal text, and pulls the two core Cyprus scrapers forward rather than leaving them in Phase 5.
**Judgement calls flagged for owner review**: (1) NVD full CVE feed deferred; CISA KEV covers exploited vulnerabilities, which is what Urgent test U-1 needs. (2) EIOPA deferred; smallest client segment, joint DORA outputs surface via EBA, ESMA, and the ESAs Joint Committee.

## D-011: Register taxonomy superseded (2026-07-07)

**Decision**: The draft taxonomy and HIGH/MEDIUM/LOW scoring sketch embedded in the source register are superseded. Authoritative versions: `taxonomy-v1.0.md` and `scoring-criteria.md`.
**Rationale**: One source of truth per artefact. Conflicting drafts in context waste tokens and risk mis-tagging.

## D-012: ENISA feed discontinued, deferred to Wave 2 as a scraper (2026-07-07)

**Decision**: ENISA moves from PoC Wave 1 to PoC Wave 2. It will be built as a scraper, not an RSS/API collector.
**Trigger**: During Phase 2 feed verification, Claude Code confirmed ENISA has no working RSS/API feed. The prior feed is discontinued and no replacement mechanism has shipped yet.
**Rationale**: Wave 1 is scoped to RSS/API only. Converting ENISA to a scraper mid-session would break that scope and pull scraper complexity forward before the RSS path is proven. Wave 2 already contains scrapers (CySEC, CBC), so ENISA belongs there. The four remaining Wave 1 sources (EBA, ESMA, CERT-EU, CISA KEV) still exercise the full pipeline across both pillars. AI security coverage is not lost; other AI-security sources remain in the register for Phase 5.
**Revisit**: If ENISA ships a new subscription or feed mechanism, prefer it over a scraper. TBD until then.

## D-013: CISA KEV per-item URL maps to NVD record (2026-07-07)

**Decision**: For CISA KEV items, the `url` field maps to the per-CVE NVD record page (verified live against nvd.nist.gov), not the KEV catalogue page. The named `source` remains CISA_KEV.
**Trigger**: KEV entries carry no per-item article URL, only a cveID and metadata. Claude Code flagged this at schema approval.
**Rationale**: The design requires every item to trace to a specific source. A constant link to the full catalogue (1,600+ entries) would undercut item-level traceability in the digest and later client-facing output. The per-CVE NVD page is stable and specific. Dedup is unaffected: content_hash includes the title, which is unique per CVE.

## D-014: KEV needs a pre-triage relevance filter (Phase 3 note) (2026-07-07)

**Decision (deferred to Phase 3)**: CISA KEV items must pass a cheap pre-triage filter before being sent to the Claude API, rather than sending the whole catalogue.
**Trigger**: The first pipeline run loaded 1,631 KEV items. Sending all of them through triage would be costly and mostly wasteful, since most are low relevance to the client base.
**Rationale**: Most KEV entries do not affect Finalogic's clients. A rules-based pre-filter (e.g. match against relevant vendors/products, aligned to Urgent test U-1) keeps API cost proportional to relevance. To be designed at the start of Phase 3.

## D-015: KEV pre-triage filter skipped for the PoC, supersedes D-014 (2026-07-09)

**Decision**: The CISA KEV pre-triage relevance filter proposed in D-014 is skipped for the PoC. Triage processes new, untriaged items from all four Wave 1 sources equally. The 1,631-item KEV backlog from the first collection run is excluded from triage. Triage starts from items collected after a cutoff date (TBD, to be agreed in the Phase 3 design pass).
**Rationale**: The backlog was a one-off catalogue load. Ongoing KEV additions are a small daily trickle, so the cost case for a pre-filter is unproven. Building a vendor/product filter now would be premature optimisation against the simple-and-boring rule.
**Revisit**: Only if KEV noise or triage cost proves material in practice.

## D-016: Triage prompt and script design (2026-07-09)

**Decision**: Triage is one Claude API call per item using model Claude Sonnet (claude-sonnet-4-6). The prompt template lives at `src/triage_prompt.md`. It does not contain pasted copies of the taxonomy or scoring criteria. The script reads `docs/taxonomy-v1.0.md` and `docs/scoring-criteria.md` at runtime and injects them into placeholders, so the locked documents remain the single source of truth and version drift is impossible. Output is a single structured JSON object per item: auto_discard, tags, level, rules_applied, summary, flagged, flag_rules, flag_reason, confidence. Every level must be justified by named rules in rules_applied. The model may apply AD-2 and AD-3 only; AD-1 (duplicates) is handled upstream by content hash. Summaries derive strictly from supplied text. Uncertainty is flagged per F-1 to F-4, never guessed. Raw item rows are never altered; triage results are written to new columns.
**Cost controls**: No batch API and no prompt caching for the PoC. At observed volume (roughly 6 items per day, about $0.02 to $0.03 per item at Sonnet 4.6 rates of $3/$15 per million tokens) both add code for savings measured in cents. Token usage and cost are logged per run from run one. Revisit at Wave 2 volume.
**Trigger**: Manual for the PoC. Local script run first (`.env` for the API key, already gitignored), then a GitHub Actions workflow_dispatch button once stable. Automatic chaining after collection is deferred; the human review gate removes any end-to-end speed benefit.
**Fetch failures**: If an item URL cannot be fetched (403, timeout, empty content), triage proceeds on title plus feed snippet with F-3 flagged, and the failure is recorded in a fetch_status column. Items are never silently skipped.

## D-017: Triage scope cutoff, per source (2026-07-09)

**Decision**: Eligibility for triage is per source, not a single date. CISA KEV items are eligible only where retrieved_at >= 2026-07-08T00:00:00Z, which excludes the 1,631-item first-run catalogue load (per D-015). Items from EBA, ESMA, and CERT-EU are eligible regardless of retrieval date, including the 30 items from the first run.
**Rationale**: The KEV first run was a catalogue dump, not news. The first-run items from the other three sources are those sources' most recent genuine publications and span consultations, guidelines, advisories, and reports, giving the triage prompt a proper shakedown set (roughly 36 items, about one dollar) instead of a 6-item, KEV-heavy one.

## D-018: Notion review board structure (2026-07-09)

**Decision**: One Notion database, one row per triaged item. Properties: Title, URL, Source (select), Published date, Level (select, the working value reviewers may change), AI Level (select, written once by sync, never edited), Themes (multi-select), Sectors (multi-select), Jurisdiction (select), Type (select), Status (select: New, Reviewed, Published, Discarded), Flagged (checkbox), Flag reason (text), Summary (text), Confidence (select), Override reason (text), item_id (number, the SQLite key used by sync). Nothing more until real review shows a gap.
**Override log**: Sync-back detects Level differing from AI Level and writes an override record to SQLite (item_id, original level, final level, reason, timestamp). This implements scoring criteria section 10 with no extra machinery. Override patterns feed Phase 5 threshold tuning.
**Direction of truth**: SQLite remains the system of record (D-008). Notion holds review state (Status, Level, Override reason) which syncs back; all other properties flow one way, SQLite to Notion.

## Open items

- TBD: MiCA theme tag. Deferred until item volume justifies it (see taxonomy section 9).
- Notion workspace structure: resolved by D-018.
- TBD: Urgent alert delivery channel (email vs other). To be decided in Phase 4.
- TBD: U-1 reference list of client-relevant systems (see scoring criteria section 12).
