# Finalogic Intelligence Pipeline: Source Register

**Status:** Active. PoC scope defined 2026-07-07.
**Version:** 1.2
**Purpose:** Master list of monitored sources for internal regulatory and cybersecurity intelligence, designed to scale into a client-facing product.

**Scope:** Financial-sector focus. Cyprus and EU priority. AI governance and AI security treated as priority cross-cutting themes.

**How to read the feed column:**
- `RSS` = feed likely available, confirm exact URL at build
- `API` = structured API available
- `Scrape` = no feed, needs a custom scraper
- `Email` = subscribe to official email alerts as primary or backup
- `TBD` = feed mechanism to verify during build

**Tiering:**
- **Tier 1** = mandatory, official, primary source. Always ingest.
- **Tier 2** = high value. Official international or high-quality specialist.
- **Tier 3** = monitor manually. Do not auto-ingest.

---

# PROOF OF CONCEPT SCOPE (v1)

The PoC ingests a deliberately small subset of Tier 1, in two waves. Everything else in this register is backlog for Phase 5. A source is in the PoC only if it appears below.

## Wave 1: RSS and API only (Phase 2 build target)

Four sources. Low build risk, covers both pillars, enough volume to exercise dedup, triage, review, and the digest end to end. (ENISA was in Wave 1 but moved to Wave 2 per D-012 after its feed was confirmed discontinued.)

| Source | Pillar | Feed | Why first |
|---|---|---|---|
| EBA | Regulatory | RSS / TBD | DORA and ICT advisory backbone |
| ESMA | Regulatory | RSS / TBD | Investment firm and MiCA coverage |
| CERT-EU | Cybersecurity | RSS / TBD | Actionable advisories, urgent-alert exerciser |
| CISA KEV catalogue | Cybersecurity | API / RSS | Highest-signal vulnerability source. Exploited-only |

## Wave 2: PoC completion (immediately after Wave 1 is stable)

Five sources. Adds the Cyprus differentiator, the AI priority theme, and authoritative EU legal text. Includes the scrapers.

| Source | Pillar | Feed | Why second |
|---|---|---|---|
| CySEC | Regulatory | Scrape | Core Cyprus value. First scraper |
| Central Bank of Cyprus | Regulatory | Scrape / TBD | Core for EMI clients. Second scraper |
| European AI Office | Regulatory / AI | RSS / Scrape | Priority AI theme |
| EUR-Lex / Official Journal | Regulatory | API / Email | Authoritative text of EU law |
| ENISA | Cybersecurity | Scrape | Core EU cyber authority, includes AI security outputs. RSS/API feed confirmed discontinued 2026-07-07 (D-012), so built as a scraper here |

## Deliberate PoC exclusions (with reason)

- **NVD full CVE feed**: Deferred. Volume is very high and mostly low relevance. CISA KEV covers exploited vulnerabilities, which is what the Urgent tests (U-1) need. Revisit in Phase 5.
- **EIOPA**: Deferred. Insurance is the smallest client segment. DORA joint outputs surface via EBA, ESMA, and the ESAs Joint Committee.
- **All other Tier 1, and all Tier 2 and Tier 3**: Backlog, Phase 5, in register order below.

---

# PILLAR 1: REGULATORY

## 1a. Cyprus National (Tier 1)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| CySEC | Circulars, announcements, policy statements, consultations, directives, enforcement | Scrape | Core. Primary regulator for our CIF, EMI, and fund clients. **PoC Wave 2** |
| Central Bank of Cyprus (CBC) | Payment institutions, EMIs, prudential, AML guidance | Scrape / TBD | Core for EMI and payment-sector clients. **PoC Wave 2** |
| MOKAS (Cyprus FIU) | AML/CFT typologies, guidance, alerts | Scrape / TBD | AML obligations for regulated clients. |
| Office of the Commissioner for Personal Data Protection (Cyprus DPA) | GDPR guidance, decisions, AI and data | Scrape / TBD | Data protection and AI overlap. |
| Official Gazette of the Republic of Cyprus | National laws, transposition, designations | Scrape / TBD | Authoritative national legal source. |
| Digital Security Authority (DSA Cyprus) | NIS2 competent authority, national cyber rules | Scrape / TBD | Bridges into Cybersecurity pillar. |

## 1b. EU Financial Regulators and ESAs (Tier 1)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| EBA | Banking, DORA RTS/ITS, ICT risk, guidelines, Q&A | RSS / TBD | Core. DORA and ICT advisory backbone. **PoC Wave 1** |
| ESMA | Securities, MiCA, reporting, supervisory briefings | RSS / TBD | Core for investment firms and crypto clients. **PoC Wave 1** |
| EIOPA | Insurance and pensions, DORA joint outputs | RSS / TBD | Completes the three ESAs. DORA is joint. |
| ESAs Joint Committee (DORA oversight) | Critical ICT third-party provider oversight, joint DORA standards and outputs | TBD | Direct DORA third-party regime. Verify exact publishing location. |
| ECB / SSM | Prudential supervision, cyber resilience expectations | RSS / TBD | Systemic and supervisory signals. |
| ESRB | Systemic risk warnings and recommendations | RSS / TBD | Macro-prudential context. |
| AMLA (EU Anti-Money Laundering Authority) | New EU AML supervisor, standards | Scrape / TBD | Rising importance for EMI and fintech AML. |
| SRB (Single Resolution Board) | Resolution, operational continuity | TBD | Lower priority. Monitor selectively. |
| European Commission (DG FISMA) | Financial services policy, consultations | RSS / TBD | Upstream of most EU financial rules. |

## 1c. EU Legislative and Official (Tier 1)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| EUR-Lex / Official Journal (OJ) | Regulations, directives, implementing and delegated acts | API / Email | Authoritative text of EU law. Use SPARQL or email alerts. **PoC Wave 2** |
| European Commission (Have Your Say) | Consultations and feedback periods | RSS / TBD | Early warning on upcoming rules. |
| EDPB | GDPR guidelines, opinions, AI and data positions | RSS / TBD | Data protection and AI enforcement direction. |
| EDPS | Supervision of EU bodies, AI and privacy opinions | RSS / TBD | Influential on AI and data policy. |

## 1d. AI Governance and Regulation (Tier 1, priority theme)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| European AI Office | AI Act implementation, guidelines, consultations, codes of practice | RSS / Scrape | Core. Active consultation feed. Drives AI Act interpretation. **PoC Wave 2** |
| European Commission (Shaping Europe's Digital Future, AI) | AI Act press releases, delegated acts, timelines | RSS / TBD | Primary AI Act news source. |
| European Artificial Intelligence Board | Coordination and guidance across member states | TBD | Governance signals. Lower volume. |
| Cyprus AI competent authority (Commissioner of Communications / Deputy Ministry of Research, Innovation and Digital Policy) | National AI Act designation, market surveillance, sandbox | Scrape / TBD | Cyprus AI enforcement point. Verify exact publishing page. |
| EUR-Lex (AI Act and delegated acts) | Binding AI legal texts | API / Email | Authoritative AI Act text and amendments. |

**Note on AI in finance:** EBA, ESMA, and EIOPA increasingly publish AI-specific guidance for financial services. Tag AI items from those sources under both the AI cluster and the relevant ICT or sector themes so they surface in either client filter.

## 1e. International Standard-Setters (Tier 2)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| BIS / Basel Committee (BCBS) | Prudential standards, operational resilience | RSS / TBD | Upstream of EU prudential rules. |
| FSB | Systemic risk, crypto asset frameworks, operational resilience | RSS / TBD | Global policy direction. |
| IOSCO | Securities markets, crypto, conduct | RSS / TBD | Relevant for investment-firm clients. |
| FATF | AML/CFT standards, grey/black lists | Scrape / TBD | AML for EMI and fintech clients. |
| MONEYVAL (Council of Europe) | AML evaluations including Cyprus | Scrape / TBD | Direct Cyprus AML relevance. |
| OECD | AI principles, policy, financial policy | RSS / TBD | AI and broader policy context. |

## 1f. High-Quality Specialist Commentary (Tier 2, use sparingly)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| IAPP | Privacy, data protection, AI governance, AI Act trackers | RSS / TBD | Excellent AI Act and privacy tracking. |
| Major EU law firm regulatory blogs (e.g. select two or three) | Practical interpretation of new rules | RSS / TBD | Context and client-ready framing. Pick two or three only. |
| Finextra (regulatory section) | Fintech and payments regulatory news | RSS / TBD | Sector signal. Filter hard. |

---

# PILLAR 2: CYBERSECURITY

## 2a. EU Official Cyber (Tier 1)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| ENISA | Threat landscape, advisories, AI security, sector guidance | Scrape | Core EU cyber authority. RSS/API feed confirmed discontinued 2026-07-07 (D-012). **PoC Wave 2, scraper** |
| CERT-EU | Threat advisories, security guidance, alerts | RSS / TBD | Core for actionable advisories. **PoC Wave 1** |
| EU NIS Cooperation Group | NIS2 implementation guidance | TBD | Regulatory-cyber bridge. |

## 2b. Cyprus National Cyber (Tier 1)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| CSIRT-CY (National CSIRT, under DSA Cyprus) | National advisories, incidents, alerts | Scrape / TBD | Cyprus-specific cyber relevance. |
| Digital Security Authority (DSA Cyprus) | NIS2 obligations, national cyber policy | Scrape / TBD | Also listed under Regulatory. Tag both. |

## 2c. Vulnerability and Threat Intelligence (Tier 1)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| NVD (NIST) | CVE records, severity scoring | API | Deferred from PoC. High volume, mostly low relevance. CISA KEV covers exploited vulnerabilities. Revisit Phase 5. |
| CVE.org / MITRE | CVE assignment and records | API / TBD | Primary CVE source. Same deferral rationale as NVD. |
| CISA (advisories + KEV catalogue) | Exploited vulnerabilities, ICS, advisories | RSS / API | KEV catalogue is high-signal. **PoC Wave 1** |
| NCSC UK | Advisories, weekly threat reports, guidance | RSS / TBD | High quality. Often EU-applicable. |

## 2d. International Cyber Agencies and Sector (Tier 2)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| FS-ISAC | Financial-sector threat intelligence | TBD / membership | Directly relevant to financial clients. Membership may apply. |
| SANS Internet Storm Center | Daily threat diary, emerging activity | RSS | Reliable daily signal. |
| Microsoft MSRC | Microsoft security updates and advisories | RSS / API | Relevant given M365 client environments. |
| SWIFT security notices | Payment infrastructure security | TBD | Relevant for payment-sector clients. |

## 2e. AI Security (Tier 2, priority theme)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| ENISA (AI security outputs) | AI threat landscape, securing AI | RSS / TBD | Covered in PoC via the ENISA Wave 1 collector. |
| NIST AI (AI Risk Management Framework) | AI risk, security, governance | RSS / TBD | Widely referenced AI risk standard. |
| OWASP (LLM and GenAI security) | LLM Top 10, GenAI security risks | Scrape / TBD | Practical AI security control reference. |
| MITRE ATLAS | Adversarial AI tactics and techniques | TBD | AI threat modelling. |
| UK AI Safety Institute (AISI) | Frontier AI risk and evaluation | RSS / TBD | Forward-looking AI risk signal. |

## 2f. Quality Cyber Commentary and Research (Tier 2, filter hard)

| Source | Covers | Feed | Relevance |
|---|---|---|---|
| Cisco Talos | Threat research and disclosures | RSS | High-quality original research. |
| Mandiant (Google) | APT and incident research | RSS / TBD | Threat actor intelligence. |
| Palo Alto Unit 42 | Threat research | RSS / TBD | Original threat intel. |
| KrebsOnSecurity | Investigative cyber reporting | RSS | High signal, low noise. |
| Schneier on Security | Policy and security analysis | RSS | Strategic context. |

---

# PILLAR 3 (cross-cutting): Manual Watch Only (Tier 3)

Do not auto-ingest. Monitor by eye. Use for early signals, not for the pipeline.

- Official regulator and agency accounts on LinkedIn and X.
- Selected senior regulatory and cyber commentators.
- Industry association newsletters not yet vetted.

**Reason:** Social and unvetted sources carry noise and misattribution risk. They undermine the credibility of an auditable product. Promote a source to Tier 1 or 2 only after it proves consistent.

---

# Tag Taxonomy

**Superseded.** The draft taxonomy previously embedded in this register was finalised and locked on 2026-07-07. The single authoritative version is `docs/taxonomy-v1.0.md`. Do not tag from this file.

Relevance scoring is likewise locked in `docs/scoring-criteria.md` (four levels: Urgent, High, Standard, Low). The earlier HIGH / MEDIUM / LOW sketch is superseded.

---

# Build Notes

1. **PoC scope governs.** Build only the Wave 1 and Wave 2 sources defined at the top of this file. Everything else is Phase 5 backlog.
2. **Confirm each feed at build.** Every `TBD` and `RSS / TBD` must be verified against the live site before coding the collector. No exact feed URLs are asserted in this register.
3. **Tag from the locked taxonomy only** (`docs/taxonomy-v1.0.md`). Sector and theme tags applied from day one are what later power client filtering.
4. **Dual-tag bridge sources.** DSA Cyprus, ENISA, and financial-regulator AI outputs sit across pillars. Tag them in both so they appear in either client filter.
5. **Verify before trusting volume.** A source earns auto-ingest status only after it proves stable and relevant.

# Version history

- v1.2 (2026-07-07): ENISA moved from Wave 1 to Wave 2 as a scraper after its RSS/API feed was confirmed discontinued (D-012). Wave 1 now four sources, Wave 2 now five.
- v1.1 (2026-07-07): PoC scope added (two waves, exclusions with reasons). Embedded draft taxonomy marked superseded by taxonomy-v1.0.md and scoring-criteria.md. Build notes aligned.
- v1.0: Initial register (pre-workspace).
