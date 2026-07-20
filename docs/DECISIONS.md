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

## D-019: Scoring criteria v1.1, rule IDs for Standard and Low (2026-07-09)

**Decision**: scoring-criteria.md is updated to v1.1. Sections 6 and 7 gain rule IDs S-1 (Standard) and L-1 (Low). Level definitions, examples, and scoring behaviour are unchanged; this only makes the two levels citable.
**Reason**: The 3-item triage pilot surfaced that v1.0 gave rule IDs to auto-discard, Urgent, High, weighting, and flagging, but left Standard and Low as prose. D-016 requires every level to be justified by a named rule in rules_applied, which was impossible for the two most common levels, so the model improvised free text. The gap was in the locked scoring document, not the code. Found at the pilot checkpoint before the full run, which is the checkpoint working as intended.
**Related prompt change**: src/triage_prompt.md placeholder renamed {{SCORING_CRITERIA_V1_0}} to {{SCORING_CRITERIA}}, and a note added: rules_applied records only the rules that determined the outcome, no considered-and-rejected reasoning, no free text. src/triage.py must be updated to fill the renamed placeholder.
**Validator**: The triage validator accepts the pattern ^(AD|U|H|W|F|S|L)-\d+$ for rules_applied entries.
**Cost**: The 3 pilot items are re-run against v1.1 (about $0.05) so the whole 36-item set carries consistent rule IDs.

## D-020: Scoring criteria v1.2, U-1 client-base clause becomes a mandatory flag (2026-07-09)

**Decision**: scoring-criteria.md is updated to v1.2. U-1's second clause (the vulnerability is in systems widely used by Finalogic or its client base) becomes a mandatory flag condition. An item that meets the critical-and-exploited clause but cannot evidence client-base relevance from the supplied text is flagged F-2 for human review with its provisional level, not finalised as Urgent. F-2's wording is extended to name this case. A matching note is added to src/triage_prompt.md.
**Reason**: The first full triage run scored 13 of 35 items Urgent, all citing U-1, on a scale whose section 4 states Urgent is narrow by design. CERT-EU and CISA KEV emit critical exploited vulnerabilities almost by definition, so U-1's first clause is nearly always true; the second clause is the real filter and the model cannot test it because the client-systems reference list does not exist (section 12 TBD). Eleven items asserted U-1 while unable to test half of it; only two flagged F-2. On the current alert design this would fire the urgent channel on nearly every CERT-EU and KEV item, defeating the channel's purpose. Chosen over building the client-systems list now (deferred, needs client-stack input, a Phase 4/5 artefact) and over deferring the fix (would bank mislabelled Urgent rows requiring re-triage later).
**Scope note**: This is a PoC-appropriate fix. The proper long-term fix is the client-systems reference list, which would let U-1 finalise as Urgent when a match is evidenced. Section 12 TBD remains open for that.
**Re-triage**: The 36-item set is re-triaged on v1.2 so the committed dataset reflects the corrected rule. Expected effect: most of the 11 U-1 items move from Urgent to F-2-flagged provisional Urgent. Cost about $0.65 to $0.75.

## D-021: Scoring criteria v1.3 and prompt fixes, two defects from the first v1.2 board (2026-07-10)

Two defects surfaced when the first full v1.2 triage was reviewed before pushing to Notion. Both are in the design documents, not the code. Neither required re-triaging the current 36-item set: the fixes apply to future runs, and any item mis-levelled under the old wording is flagged for human review anyway, so the reviewer corrects it at the gate.

**Defect 1 (resolved, scoring-criteria v1.3)**: v1.2's U-1 said a flagged item keeps "its provisional level" but never defined that level. In the first v1.2 run, ten items cascaded Urgent to High (citing H-4) and three held Urgent, on the same rule and similar inputs. v1.3 defines the provisional level as the level the item would hold absent any Urgent test (High via H-4 for broad-impact cyber items short of Urgent), not Urgent. The prompt note is updated to match. Chosen reading: cascade to High, because "not finalised as Urgent" should not leave the item sitting at Urgent, and H-4 exists precisely for serious cyber items short of the Urgent tests.

**Defect 2 (resolved in prompt, validator fix pending)**: Twelve of thirteen flagged items put F-2 in rules_applied, but per the prompt, flag rules belong in flag_rules and rules_applied holds only level, weighting, and discard rules. The validator regex ^(AD|U|H|W|F|S|L)-\d+$ accepted F- in rules_applied, so prompt and validator disagreed. The prompt now states F rules go in flag_rules, not rules_applied. Pending code change: tighten the rules_applied validator to ^(AD|U|H|W|S|L)-\d+$ (drop F), and validate flag_rules separately as ^F-\d+$. Flagged for the next code session; not a re-triage trigger.

**Current board note**: The 36 items on the board were triaged under v1.2, so the three held-Urgent items and the F-2-in-rules_applied entries persist there. They are all flagged, so the reviewer sees and can correct them. The board is not rebuilt for this; v1.3 governs the next run.

## D-022: Sync-back reads the original level from SQLite, not from the Notion display copy (2026-07-10)

**Decision**: `pull()` in `src/notion_sync.py` takes `original_level` for an override row from `items.level` in SQLite, never from the Notion AI Level property. Where a page's AI Level disagrees with `items.level`, sync-back refuses to log an override for that item, prints a warning naming the item and both values, and exits non-zero. Status is still written back for that item, since review state is unaffected by the mismatch. Restoring an edited AI Level stays a manual repair against `items.level`: sync-back still writes nothing to Notion.
**Trigger**: In the Phase 3 sync-back test, AI Level was edited on the board instead of Level. The two are adjacent columns. `pull()` read the board's AI Level as the original level and wrote an overrides row asserting the model scored item 3365 Standard and a human raised it to High. The model scored it High and the working Level was never changed. The row was a fabrication and nothing in the code noticed.
**Rationale**: The override log is the Phase 5 threshold tuning dataset. A mis-click must never be able to write a false audit record into it. D-008 makes SQLite the system of record and D-018 flows every property except Status, Level and Override reason one way, SQLite to Notion, so AI Level in Notion is a display copy. Reading truth from the copy contradicted both. Under D-018 AI Level is written once and never edited, so a disagreement can only be a mis-edit, never a real override. Exiting non-zero keeps the integrity warning visible rather than silent, per D-009.

## D-023: Client matching design, and phases renumbered (2026-07-14)

Recorded retrospectively. Phase 4 built the matching layer; this entry states the design it settled on and fixes the phase numbering it broke.

**Matching design**: Client interest profiles are built only from tags in the locked taxonomy (`config/clients.yaml`, validated at seed time by `src/clients.py`; an unknown tag fails loudly and nothing is seeded). An item matches a client when it shares at least one sector, jurisdiction, or theme tag AND its level is at least as urgent as the client's `min_level`. The match is scored by weighted overlap: jurisdiction 3, sector 2, theme 1, because jurisdiction and sector route a regulatory item more strongly than a shared theme does. Every match records `matched_on`, naming the tags that caused it.
**No AI in matching**: The engine is deterministic. AI classifies and summarises (D-002); routing is a rule. A model deciding which client sees what would be unauditable and could not be explained to a client.
**Human gate enforced in matching**: Only items with `review_status` in ('Reviewed', 'Published') are matched. `preview` matches every triaged item for testing and never writes.
**Ledger**: `matches(item_id, client_id, score, matched_on, created_at, delivered_at)`, primary key (item_id, client_id). Re-running updates score and matched_on for a pair and never clears `delivered_at`. `delivered_at` was added here but left unused until Phase 5 claimed it.

**Phase renumbering**: Client matching was built as Phase 4 and distribution as Phase 5, but the roadmap already used those numbers for internal delivery and coverage expansion. Coverage expansion moves to Phase 6 and white-label to Phase 7. `docs/ROADMAP.md` is authoritative. D-015, D-018, and D-020 were written earlier and say "Phase 5" where they mean coverage expansion and scoring threshold tuning; read those as Phase 6. History is not edited (this log's own rule), so the note is carried here and in the roadmap instead.
**Reason**: Two documents were using "Phase 5" to mean different things, and `CLAUDE.md` still told a fresh session that Phase 2 was active. The next session would have started from a wrong map.

## D-024: Distribution design (2026-07-14)

**Decision**: Distribution is a set of output plugins under `src/distribute/`, symmetric with `src/collectors/` for intake. The deterministic core sits between them.

**Digest** (`digest.py`): Per client, gather every match where `delivered_at IS NULL`, join to the item, group by level (Urgent, High, Standard, Low), and render Markdown. Each entry shows the title, source, published date, link, the item's existing `ai_summary`, and the `matched_on` reason. Where an item was flagged at triage, the flag reason is shown too: it reached the client only because a human reviewed it and let it through, so it is stated rather than hidden.
**No model calls in distribution**: The digest reuses the summary triage already wrote and a human already approved. Summaries derive strictly from fetched text (hard rule 2). An LLM-written executive summary would be a new claim about the items that no reviewer saw, and is a separate decision, not this one.
**Channels** (`channels.py`): One channel per destination behind a `deliver` interface, selected by `config/distribution.yaml`, never named at the call site. Built: `file` (writes `data/digests/<client>/<date>.md`) and `console`. An unknown channel name is fatal, never a silent fallback to console, because a fallback would look like a successful send and mark matches delivered that nobody received.
**Email deferred**: SendGrid is already the locked distribution stack (D-003), so adding it is executing a made decision, not a new one. It is still out of scope here: every client in `config/clients.yaml` is an example, so there is nobody real to send to, and a session also writing its first tests should not carry a live-send blast radius. Email is Phase 7.
**Idempotency**: `delivered_at` is the key. It is written only after a channel reports success. A delivered match is never re-sent; a failed send leaves it null and the next run retries it. Re-running distribution immediately produces nothing.
**Human gate re-asserted at send**: Distribution independently checks `review_status` in ('Reviewed', 'Published') even though matching already did. A match row is written once and read later, and a reviewer can move an item back to New or Discarded on the board in between. The gate is the product promise, so it is checked where the sending happens, not only where the matching happened.
**Orchestrator** (`pipeline.py`): Runs collect, triage, push, pull, match, distribute in order and stops at the first failure, because each stage consumes the one before it. `triage` and `distribute` are opt-in on a live run, since one spends money and the other sends things. `--dry-run` previews every stage and writes, sends, and charges nothing.
**Digests are not committed**: `data/` is gitignored. Digests rebuild from the database at any time, and the ledger already records what was sent and when, so committing them would add churn without adding an audit trail.
**Tests** (`tests/`, pytest): Cover the matching rule, triage output validation, the taxonomy parser, and the human gate plus idempotency. These are the places where a regression is silent: it shows up as an unreviewed item in a client's inbox or a digest sent twice, not as an error. Tests run against a temporary database built by the real schema code, never against `finalogic.db`. pytest is the only new dependency and ships nothing to production.
**D-021 defect 2 closed here**: The pending validator fix was applied. `rules_applied` now accepts only `^(AD|U|H|W|S|L)-\d+$` and `flag_rules` is validated separately as `^F-\d+$`. Prompt and validator now agree. Not a re-triage trigger: the 12 affected rows are all flagged, so a reviewer sees them, and the fix governs future runs.

## D-025: Database stays in git for the PoC, workflow serialised (2026-07-14, decided 2026-07-16)

**Problem**: `finalogic.db` is a 1.1 MB SQLite binary committed to the repository and rewritten by the daily Action. It cannot be diffed or merged. Concurrent runs can race on push, and `.github/workflows/collect.yml` pushes without a pull or rebase, so a racing push simply loses. Every collection run adds a full copy of the file to git history.
**Why it has not bitten yet**: Item volume is low and there is one operator. Wave 2 (Phase 6) adds five sources including scrapers, which raises both the write rate and the size.
**Options weighed**: a hosted Postgres (Supabase, Neon); keeping SQLite but hosting the file (Litestream, Turso); or keeping the current design and serialising the workflow with a concurrency group, which fixes the race but not the diffing or the history bloat.
**Decision (2026-07-16)**: The database stays committed to git for the PoC. The race is fixed in the workflow: a concurrency group serialises collection runs, and the job rebases onto origin before pushing, so a non-conflicting remote change no longer loses the push. A rebase conflict on the binary fails the job loudly (per D-009) rather than losing data silently. History bloat and undiffability are accepted at PoC scale.
**Revisit**: Before a client-facing launch, move the file to hosted SQLite (Turso, or Litestream to object storage). Postgres is not justified at this volume and would rewrite working code for no capability gain. D-008 is unchanged: SQLite remains the system of record; only where the file lives was in question. D-008 (SQLite as system of record) is not in question here; where the file lives is.

## D-026: Triage provider is kie.ai, not the Claude API. Supersedes D-003 and D-016 on model choice (2026-07-14)

**Decision**: Triage calls a model through kie.ai, which serves models on a Gemini-compatible API. Default model `gemini-3-5-flash`, configured by `KIE_MODEL` in the environment. The Anthropic SDK is removed as a dependency. D-003 (which named the Claude API) and D-016 (which named `claude-sonnet-4-6`, its pricing, and its cost controls) are superseded on model choice only. Everything else in D-016 stands unchanged: one call per item, the prompt template at `src/triage_prompt.md`, the locked documents injected at runtime, the same structured JSON output, validation before write, and raw item columns never altered.

**Trigger**: The Anthropic account is out of credit. The kie.ai account has credit. The pipeline could not run.

**Rationale**: The model is the one component in this design that was always meant to be replaceable. The value of the system is in the parts that are not the model: named-source traceability, the locked taxonomy, the scoring rules, the validator that rejects anything outside them, and the human gate. That claim was tested rather than assumed before this decision was taken. The same prompt, the same locked documents and the same validator were run against `gemini-3-5-flash` on three live items, and all three produced in-taxonomy tags and rule-justified levels that passed validation first time, with no retries and no code changes above `src/llm.py`.

**Structure**: All model-aware code is now in `src/llm.py`, roughly a hundred lines calling one HTTP endpoint. Changing model or provider again is a change to that file and the environment, nothing else. `triage.py` does not know what model answered. `items.model` records what actually produced each row, so the 36 rows triaged on `claude-sonnet-4-6` remain attributable and are not silently reattributed.

**Cost**: Roughly $0.002 per item against roughly $0.021 on Sonnet, so about $5 a year against about $45 at current volume. The saving is not the reason for the change; the empty wallet is. The pricing constants in `triage.py` are marked TBD until verified against the kie.ai price list. They are used only to report the cost of a run and cannot affect triage output.

**Risks accepted, and what to watch**:
1. **Under-flagging is the failure mode to watch, not bad tags.** The Claude run flagged 13 of 36 items (36%). The three-item Gemini Flash sample flagged none. Three routine items is far too small a sample to conclude anything, and all three were genuinely Standard, but flagging is where a weaker model is dangerous: an item that should have been flagged for a human simply looks confident, and passes the gate unexamined. Tag validity is the easy property; calibrated uncertainty is the hard one, and the F rules exist to capture it. Review the flag rate after the next full run. If it is materially below the Claude baseline on comparable items, raise `KIE_THINKING_LEVEL` to `high` or move to a stronger model slug (kie.ai also serves `claude-haiku-4-5`).
2. **Third-party proxy.** kie.ai is a reseller sitting in front of the model provider. For a firm advising regulated clients on ICT third-party risk, this is the kind of dependency that belongs in its own register of information. Items sent to it are public regulatory and security publications, not client data, which bounds the exposure. Revisit before any client-confidential content enters the pipeline.
3. **The existing 36 rows were triaged on a different model.** They are not re-triaged. The dataset is therefore mixed, and `items.model` is what distinguishes it. Re-triage on one model before the override log is used for scoring threshold tuning (Phase 6), or the tuning dataset conflates two models' behaviour.

**Reversal**: Set `KIE_MODEL` to another slug, or restore an Anthropic client in `src/llm.py`. Nothing above that file changes. That is the point of the structure.

## D-027: ECB/SSM added to PoC scope, built after the Cyprus scrapers (2026-07-16)

**Decision**: ECB/SSM joins the PoC source list as a scope addition beyond the locked Wave 2 list. It is built as an RSS collector in the existing Wave 1 pattern, sequenced after the CySEC and CBC scrapers.
**Rationale**: Owner request. ECB/SSM is Tier 1 in the register (prudential supervision, cyber resilience expectations for significant institutions) and cheap to add if the RSS feed verifies. The Cyprus scrapers stay first: they are the commercial differentiator and the largest coverage gap, while ECB content partially overlaps what EBA and ESMA already provide.
**Scope note**: D-010 ("build only Wave 1 and Wave 2") is amended by this entry, not broken ad hoc: the PoC list is now Wave 1, Wave 2, plus ECB/SSM. The register rule stands: the feed URL must be verified against the live site before the collector is coded.

## D-028: Matching requires a shared sector or theme; jurisdiction alone is not a match (2026-07-20)

**Decision**: An item matches a client only if they share at least one sector or theme tag. A shared jurisdiction on its own no longer creates a match. When a match already exists on a sector or theme, a shared jurisdiction still adds to the score and is still named in `matched_on`, so it remains a routing signal, just not a standalone reason. This supersedes the overlap clause of D-023 only; the level gate, the weights (jurisdiction 3, sector 2, theme 1), the "no AI in matching" rule, and the ledger design all stand.

**Trigger**: The first full match run over the reviewed backlog produced 138 item-client pairs, most of them noise. In the Cyprus EMI digest, about 26 of 32 items matched on `jurisdiction: EU` and nothing else, including a run of CERT-EU vulnerability advisories the EMI profile never asked for (its themes are DORA, ICT incident reporting, Payments and e-money, AML and financial crime, with no cyber theme). Because nearly every item and every client is EU, jurisdiction-only overlap routed almost everything to almost everyone.

**Rationale**: Jurisdiction is too broad to be a relevance signal by itself under the current source set. Sector and theme are what express a client's actual interest, so requiring one of them is the smallest change that removes the flood without touching the weights, the level gate, or the taxonomy. Jurisdiction keeps its scoring weight because it still routes same-jurisdiction items more strongly, and it is the mechanism that will prioritise Cyprus items over EU-wide ones once the Cyprus sources land (scoring W-2).

**Effect**: Clients now receive only items sharing a sector or theme in their profile. A client that wants cyber advisories lists the relevant theme; one that does not no longer receives them. This does not fix CISA KEV per-CVE noise, which still reaches themed clients on the cyber theme and needs the client-relevant systems list (scoring section 12); that is a separate change.

**Not a re-triage trigger**: Triage output is unchanged; only routing changes. The example-client match ledger was rebuilt under the new rule. No real client data exists yet, so nothing of value was rewritten.

## Open items

- TBD: MiCA theme tag. Deferred until item volume justifies it (see taxonomy section 9).
- Notion workspace structure: resolved by D-018.
- TBD: Urgent alert delivery channel. Partly addressed by D-024: the channel interface exists and file and console are built. What is still open is whether Urgent items get their own immediate path rather than waiting for the next digest. Needs the email channel first (Phase 7).
- TBD: U-1 reference list of client-relevant systems (see scoring criteria section 12). Still the proper fix for D-020.
- RESOLVED 2026-07-16: D-025 decided. The database stays in git for the PoC with the collection workflow serialised; hosted SQLite is the pre-launch revisit.
- TBD: Replace the example clients in `config/clients.yaml` with real ones. Nothing can be sent to a real recipient until this happens, which is deliberate.
