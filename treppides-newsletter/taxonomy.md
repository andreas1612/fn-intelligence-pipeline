# Treppides Newsletter — Tag Taxonomy (draft v0.1)

> **Status:** Draft for review. This replaces the Finalogic `taxonomy-v1.0.md`
> (which was ICT/cyber/DORA-centric — wrong domain for an audit/tax/accounting firm).
> Parent spec: [DELIVERABLE.md](DELIVERABLE.md). Routing map: [departments.yaml](departments.yaml).

Every collected item is tagged on four axes. Routing to departments is driven by
**Theme**. Jurisdiction, Type, and Source category refine weight and presentation but
never decide the destination on their own (lesson D-028).

- **Theme** — what the item is about. 1 to 3 tags. **Drives department routing.**
- **Jurisdiction** — where it applies. Exactly 1.
- **Type** — what kind of document it is. Exactly 1.
- **Source category** — authority or journal. Exactly 1 (comes from the source, not the AI).

Tag only from this document. No ad-hoc tags. `other` is the escape valve.

---

## 1. Theme tags (choose 1 to 3) — the routing axis

### 1.1 Taxation
- **direct-tax** — corporate & personal income tax, tax rulings, tax law changes.
- **vat** — VAT / indirect tax, EU VAT, place-of-supply, customs & excise.
- **transfer-pricing** — TP rules, documentation, APAs, benchmarking.
- **international-tax** — OECD/BEPS, Pillar Two, DAC (DAC6/DAC7/DAC8), double-tax treaties, tax transparency.
- **tax-administration** — Tax Department procedures, deadlines, TFA/portal, e-filing, penalties.

### 1.2 Audit & assurance
- **auditing-standards** — ISA and audit methodology developments.
- **audit-quality** — ISQM/ISQC, inspections, audit oversight (e.g. CyPAOB).
- **ethics-independence** — IESBA Code, independence, professional conduct.

### 1.3 Financial reporting
- **ifrs** — IFRS/IAS standards, amendments, interpretations (IASB/IFRIC).
- **financial-reporting** — corporate reporting, filing/disclosure requirements, GAAP.
- **sustainability-reporting** — CSRD/ESRS, ISSB, ESG disclosure.

### 1.4 Regulatory & compliance (ICAS cluster)
- **aml-cft** — AML/CFT obligations, sanctions, KYC, FATF/MOKAS, beneficial ownership.
- **investment-firm-regulation** — MiFID II/MiFIR, CIF conduct & prudential (IFR/IFD).
- **licensing-authorisation** — CySEC/CBC authorisation, CIF/EMI/PI/CASP licensing, crypto/MiCA.
- **regulatory-compliance-risk** — internal audit, governance, risk management, regulatory reporting, NIS2 governance.
- **payments** — payment services & e-money: PSD2/PSD3/PSR, strong customer authentication (SCA), instant payments, EMIs and payment institutions.

### 1.5 Funds
- **fund-regulation** — AIFMD, UCITS, fund rules and supervision.
- **fund-administration** — administration, depositary, valuation, servicing.

### 1.6 Corporate & statutory
- **company-law** — company law, corporate governance, statutory obligations.
- **registrar-filings** — Registrar of Companies, annual returns, filings, gazette designations.

### 1.7 Technology (the ICT/cyber slice — mainly the Technology department)
- **ict-operational-resilience** — DORA, ICT risk, operational resilience, third-party/ICT outsourcing.
- **cybersecurity** — threat advisories, vulnerabilities, incidents, NIS2 technical.
- **data-protection** — GDPR, privacy, data-protection guidance and decisions.
- **ai-regulation** — AI Act, AI governance and guidance.

### 1.8 People
- **employment-law** — labour law, employment regulation, work permits.
- **social-insurance-payroll** — social insurance, GHS/GESY, payroll obligations, contributions.

### 1.9 Cross-cutting / escape
- **economic-general** — macro/economic, budget, general firm-relevant developments not covered above.
- **other** — nothing fits confidently. **Auto-archived, routed to nobody** (no human to review under full autonomy). Recurring `other` on similar items is the trigger to add a theme.

**Total theme tags: 25.**

---

## 2. Jurisdiction tags (choose exactly 1)
- **cyprus** — Cyprus national instruments and publications (CySEC, CBC, Tax Dept, ICPAC, Registrar, Gazette, local bodies). **Prioritised** — closest to the firm's work.
- **eu** — EU-level (European Commission, EUR-Lex, EBA/ESMA/EIOPA, EDPB, European AI Office).
- **international** — outside EU/Cyprus (OECD, IFRS Foundation, IAASB, IESBA, FATF, foreign advisories). Includes KT HK material.

---

## 3. Type tags (choose exactly 1)
- **legislation** — laws, regulations, directives, delegated/implementing acts.
- **guidelines-standards** — standards, RTS/ITS, guidelines, recommendations, Q&As, exposure drafts.
- **consultation** — open consultations, discussion papers, calls for evidence.
- **circular-supervisory** — circulars, announcements, supervisory statements, speeches with weight. (CySEC Circulars / Announcements / Policy Statements land here.)
- **enforcement** — fines, sanctions, decisions, public censures, warnings.
- **report-publication** — studies, reports, thematic reviews, annual publications, factsheets.
- **news-commentary** — journal/press articles and analysis. (Mostly the journal category.)

---

## 4. Source category (exactly 1 — set by the source, not the AI)
- **authority** — primary/official body. Can reach any urgency level.
- **journal** — trade press / commentary. **Capped**: never top urgency, filtered harder, defaults lower; deduped against the authority original.

---

## 5. Urgency levels (scoring, refines presentation not routing)
- **Urgent** — needs attention before the next cycle (deadline < 30 days, immediate-effect rule, direct enforcement on the firm's work). Authority sources only.
- **High** — significant development for a department's practice area.
- **Standard** — relevant, worth knowing.
- **Low** — marginal; archived/searchable, not surfaced by default.

Weighting notes:
- **Cyprus** items default one level higher than equivalent EU/International (closest to client work).
- **Journal** items are capped below Urgent regardless.
- Low-confidence or `other` items are archived, never published (full-autonomy handling).

---

## 6. Tagging rules
1. Every item gets exactly one Type, exactly one Jurisdiction, one Source category, and 1 to 3 Themes.
2. Tag what the item is **substantively about**, not everything it mentions.
3. Prefer the most specific theme; a CySEC AML circular is `aml-cft` (+ maybe `licensing-authorisation`), not a generic tag.
4. No ad-hoc tags. New themes require a version bump to this file.
5. If no theme fits confidently, use `other` — it is archived, not routed.

---

## 7. Change control
- Versioned; changes are a new version of this file.
- Review trigger: quarterly, or when `other` accumulates a recurring pattern (that pattern becomes a proposed new theme).
- The triage prompt injects this file verbatim at runtime — this document is the single source of truth for tags.

## 8. Version history
- v0.1 (2026-07-23): Initial draft. Domain re-based from Finalogic (cyber/DORA) to Treppides (audit/tax/accounting/regulatory). Sector axis dropped as redundant with Theme for internal department routing.
