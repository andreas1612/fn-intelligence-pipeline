# Treppides Newsletter - Source Register (draft v0.1)

> **Status:** Draft for review. Replaces the Finalogic source register (regulatory/cyber).
> Parent spec: [DELIVERABLE.md](DELIVERABLE.md) · themes: [taxonomy.md](taxonomy.md).

Two categories, which become the two on-page sections and drive weighting:

- **authority** - primary/official body. Can reach any urgency.
- **journal** - trade press / commentary. Capped below Urgent, filtered harder, deduped against the authority original.

**Routing is by content, not by this table.** The "Typical themes" column is *what a
source tends to publish*, for planning coverage - it is NOT how items are routed. Every
item is tagged individually at triage and routed on its own tags. A source that usually
feeds one department will still fan out when an item's content says so.

Feed column: `RSS` (feed likely), `API`, `Scrape` (no feed - custom scraper), `TBD` (verify at build).
**Every feed/scrape target is verified against the live site before its collector is coded.**

---

## SECTION 1 - Regulatory Authorities

### 1a. Cyprus (priority)

| Source | Category | Feed | Typical themes |
|---|---|---|---|
| **CySEC** | authority | Scrape (per section, see below) | licensing-authorisation, investment-firm-regulation, aml-cft, fund-regulation |
| **Central Bank of Cyprus (CBC)** | authority | Scrape / TBD | aml-cft, licensing-authorisation (EMI/PI), regulatory-compliance-risk |
| **Cyprus Tax Department** (incl. TFA portal, circulars) | authority | Scrape / TBD | direct-tax, vat, tax-administration, international-tax |
| **Registrar of Companies & Intellectual Property** | authority | Scrape / TBD | registrar-filings, company-law |
| **Official Gazette of the Republic** | authority | Scrape / TBD | legislation, company-law, registrar-filings |
| **MOKAS** (Cyprus FIU) | authority | Scrape / TBD | aml-cft |
| **Commissioner for Personal Data Protection** (Cyprus DPA) | authority | Scrape / TBD | data-protection |
| **ICPAC** (Institute of Certified Public Accountants of Cyprus) | authority | RSS / TBD | auditing-standards, ethics-independence, aml-cft, ifrs, tax-administration |
| **CyPAOB** (audit oversight) | authority | TBD | audit-quality, auditing-standards |
| **Digital Security Authority / CSIRT-CY** | authority | Scrape / TBD | cybersecurity, ict-operational-resilience |
| **Deputy Ministry of Research, Innovation & Digital Policy** | authority | TBD | ai-regulation, data-protection |

### 1b. EU

| Source | Category | Feed | Typical themes |
|---|---|---|---|
| **European Commission - Taxation & Customs (TAXUD)** | authority | RSS / TBD | vat, direct-tax, international-tax |
| **EUR-Lex / Official Journal** | authority | API / Email | legislation (all themes) |
| **EBA** | authority | RSS | aml-cft, investment-firm-regulation, ict-operational-resilience |
| **ESMA** | authority | RSS | investment-firm-regulation, fund-regulation, licensing-authorisation |
| **EIOPA** | authority | RSS | (insurance-adjacent) regulatory-compliance-risk |
| **EDPB** | authority | RSS | data-protection |
| **European AI Office / Shaping Europe's Digital Future** | authority | RSS | ai-regulation |
| **ENISA / CERT-EU** | authority | Scrape / RSS | cybersecurity, ict-operational-resilience |

### 1c. International standard-setters

| Source | Category | Feed | Typical themes |
|---|---|---|---|
| **IFRS Foundation / IASB / IFRIC** | authority | RSS / TBD | ifrs, financial-reporting |
| **ISSB** | authority | RSS / TBD | sustainability-reporting |
| **IAASB** | authority | RSS / TBD | auditing-standards, audit-quality |
| **IESBA** | authority | RSS / TBD | ethics-independence |
| **IFAC** | authority | RSS / TBD | auditing-standards, ethics-independence |
| **OECD - Tax** | authority | RSS / TBD | international-tax, transfer-pricing |
| **FATF** | authority | Scrape / TBD | aml-cft |
| **MONEYVAL** (Council of Europe) | authority | Scrape / TBD | aml-cft |

---

## SECTION 2 - Journals / Industry News

Capped below Urgent, filtered hard, deduped against authority originals. Global fintech
press is high-relevance for **Licensing / Funds / Investment-firm** work and mostly noise
elsewhere - which is fine, because content routing sorts that out per item.

| Source | Category | Feed | Typical themes |
|---|---|---|---|
| **Finance Magnates** | journal | RSS / TBD | licensing-authorisation, investment-firm-regulation, fund-regulation |
| **International Tax Review** | journal | RSS / TBD | international-tax, transfer-pricing, direct-tax |
| **Tax Notes (International)** | journal | RSS / TBD | international-tax, direct-tax, vat |
| **Accountancy Europe** | journal | RSS / TBD | ifrs, auditing-standards, sustainability-reporting |
| **IFLR** | journal | RSS / TBD | investment-firm-regulation, company-law |
| **Reuters - Regulatory / Legal** | journal | RSS / TBD | economic-general, aml-cft |
| **Cyprus business press** (Cyprus Mail business, In-Cyprus, StockWatch) | journal | RSS / TBD | economic-general, tax-administration, company-law |

> Add journals sparingly. Each one added multiplies volume that triage must sort; the
> value is signal, not coverage. Promote only sources that prove consistently relevant.

---

## CySEC - section breakdown (the "many sections" care point)

CySEC is one authority publishing many section types across many subject areas. Collect
each relevant section as its own target so nothing is missed and nothing over-collected.
The **section maps to the `type` tag, never to a department** - department routing comes
only from the content themes the AI assigns.

| CySEC section | -> `type` tag | Notes |
|---|---|---|
| Announcements | circular-supervisory | General notices. |
| Circulars | circular-supervisory | The main obligation stream; spans AML, funds, CIF conduct, crypto. |
| Consultation Papers | consultation | Draft rules; route by subject. |
| Policy Statements | circular-supervisory | Final policy positions. |
| Directives | legislation | Binding rules. |
| Decisions / Enforcement | enforcement | Fines, settlements, licence actions. |
| Warnings | enforcement | Unauthorised-entity/investor warnings. |
| Forms / RegTech / XBRL | report-publication | Mostly operational; usually Low. |

Example fan-out (same source, different destinations, decided by content):
- CySEC Circular on AML checks -> `aml-cft` -> **ICAS/Compliance**, **Internal Compliance & Client Acceptance**.
- CySEC Directive on AIF authorisation -> `fund-regulation` + `licensing-authorisation` -> **Funds**, **ICAS/Licensing**.
- CySEC Consultation on CASP/crypto rules -> `licensing-authorisation` (+ maybe `ict-operational-resilience`) -> **ICAS/Licensing** (+ **Technology**).

---

## Build notes

1. **RSS first, scrapers second.** EU bodies, IFRS/IASB, OECD, and most journals are RSS;
   the Cyprus authorities (CySEC, CBC, Tax Dept, Registrar) are the scrape effort and the
   real build risk. Prove the RSS path end to end, then take the scrapers.
2. **Verify every feed/scrape target live before coding** its collector. Assert no exact
   URLs in this register until verified (record evidence, mirroring the Finalogic
   feed-verification discipline).
3. **Category is metadata, not routing.** It sets the on-page section and the urgency cap.
4. **Dedup across categories** so a journal echo of an authority action does not
   double-post to a department.
5. **Health checks per source** - a silent zero-item source must fail visibly, not pass
   as a quiet no-op.

## Version history
- v0.1 (2026-07-23): Initial draft. Authorities + journals split; CySEC sections broken out; Treppides audit/tax/accounting domain.
