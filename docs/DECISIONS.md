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

## Open items

- TBD: MiCA theme tag. Deferred until item volume justifies it (see taxonomy section 9).
- TBD: Notion workspace structure. To be designed in Phase 3.
- TBD: Urgent alert delivery channel (email vs other). To be decided in Phase 4.
- TBD: U-1 reference list of client-relevant systems (see scoring criteria section 12).
