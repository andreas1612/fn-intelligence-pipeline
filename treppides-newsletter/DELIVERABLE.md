# Treppides Hub — Newsletter / Intelligence Feed

> **Status:** BUILT (standalone) — pre hub-integration. The full pipeline runs
> end to end: **19 sources**, ~330+ items, AI triage, deterministic per-department
> routing, and a web UI (department view + search/explore). Runs locally; not yet
> wired into the hub. Service + how-to: [newsletter-service/README.md](newsletter-service/README.md).
> **Owner:** Andreas Pieri · **Created:** 2026-07-23 · **Updated:** 2026-07-23
> Companion docs: [taxonomy.md](taxonomy.md) · [departments.yaml](departments.yaml) · [sources.md](sources.md)

---

## 0. What we are delivering (read this first)

A **per-person regulatory & industry news feed inside the Treppides Hub**. Every
employee opens the hub and sees a newsletter scoped to **their department** — the
VAT team sees VAT and indirect-tax developments, the Technology team sees ICT/DORA
and cyber, Audit sees auditing standards and IFRS, and so on. Nobody wades through
everyone else's noise.

Two on-page sections:

1. **Regulatory Authorities** — primary sources (CySEC, CBC, Cyprus Tax Department,
   IFRS/IASB, ICPAC, EU bodies, …). These carry real obligations.
2. **Journals / Industry News** — commentary and trade press (e.g. Finance Magnates,
   tax/audit journals). Awareness, not obligation. Filtered harder, capped lower.

Both sections are already department-scoped. Routing is decided by **what each item
is about (its content), never by which website it came from**.

**Three properties define this deliverable:**

- **Full autonomy** — collect → triage → match → publish runs end to end with **no
  human in the loop**. No editorial gate, no approval queue. (See §3.)
- **Different for each person** — the feed is scoped to the logged-in user's
  department, resolved from their identity. (See §4.)
- **Context-level routing** — items are sorted by AI-assigned topic tags, not by
  source or URL. One authority (CySEC) fans out to many departments by content.
  (See §5.)

---

## 1. The reference architecture is NOT absolute

This project **adapts** the architecture in `newsletter/fn-intelligence-pipeline`
(built for Finalogic Ltd, an infosec/regulatory advisory firm). That pipeline is a
**reference, not a mandate.** We keep the parts that solve our problem and drop the
parts that were specific to Finalogic's use case.

### Dropped (not needed here)

| Finalogic component | Why we drop it |
|---|---|
| **Notion human-review gate** | We want full autonomy. No human approves items before staff see them. |
| **`review_status` / approval workflow** | Same reason — nothing waits on a reviewer. |
| **External client model (`clients.yaml`)** | Our audience is internal **departments**, not external clients. |
| **Cyber/DORA-only taxonomy** | Wrong domain. Treppides is audit/tax/accounting; the taxonomy is rewritten (see [taxonomy.md](taxonomy.md)). ICT/cyber survives only as the **Technology** department's slice. |
| **File / Markdown / SendGrid distribution** | Delivery is into the **hub UI**, not files or email. |

### Kept (the engine that already works)

| Reused | Note |
|---|---|
| Collector plugin pattern (one module per source), dedup by content hash, per-source health checks, scheduled run | Add Treppides sources; no engine change. |
| AI triage: fetch article → tag against a controlled taxonomy → validate → record provenance & cost. Model behind `src/llm.py`, swappable. | Reused; taxonomy content is replaced. |
| **Deterministic tag → profile matcher** (the "context-not-URL" router; one item routes to many profiles; every match records *why*) | The heart of this deliverable. Client profiles become **department profiles**. |
| Lesson **D-028**: match on shared **topic**, never on jurisdiction/source alone | Directly prevents "everything from CySEC goes to everyone". |
| SQLite as the collection/triage system of record; additive migrations | Kept. A thin read layer exposes it to the hub. |

> **Rule for this build:** where the Finalogic design and our need disagree, our need
> wins, and the divergence is documented here. Do not port Finalogic assumptions
> (human gate, clients, cyber-first taxonomy) just because they exist in the repo.

---

## 2. Where it lives

A **new FastAPI backend service** on the production server (`192.168.0.221`),
following the same pattern as the hub's other backends (`companies-api`,
`valuation-api`, `staff-directory`). Not a fork of the Finalogic repo — a new service
that reuses the Finalogic *design*.

**Built standalone first, integrated into the hub second.** For now this is an
**independent component** — its own service and its own page — runnable and demoable on
its own, with a **department selector** standing in for real identity (the same trick the
Performance page used with its dev impersonation dropdown). Only once the feed is proven
does it get wired into the hub: identity-based department resolution, sidebar/home-page
placement, tier gating, nginx, and scheduled collection. See §10.

```
newsletter-api  (new FastAPI service, e.g. port 8004)
  ├── collectors/     intake plugins, one per source        (pattern reused)
  ├── triage          AI tagging against Treppides taxonomy  (engine reused)
  ├── matching        tag → department routing               (engine reused)
  ├── store           SQLite: items + tags + routes          (pattern reused)
  └── api             GET /api/newsletter?...  (department-scoped read for the hub)

Hub frontend
  └── components/pages/newsletter.js   new section, two tabs (Authorities / Journals)

nginx  → /api/newsletter/* → 127.0.0.1:8004
```

---

## 3. Full autonomy (no human gate)

The cycle runs unattended on a schedule:

```
collect → triage (AI tags each item) → match (tags → departments) → publish to hub
```

No Notion, no approval step. Consequences and how we handle them, without adding a
human back in:

- **Mis-tagging risk.** With no reviewer, a wrong tag reaches staff. Mitigations that
  stay autonomous:
  - **Low-confidence / `Other`-tagged items are archived, not shown.** They do not
    route to any department by default. (In Finalogic these were flagged *to a human*;
    here there is no human, so they simply do not publish. They remain queryable.)
  - **Journals are capped** (never top-level urgency, filtered harder) so the noisiest
    sources cannot dominate a feed. (§5.)
  - Triage **confidence** and the **matched-on reason** are stored on every published
    item, so if a feed looks wrong the cause is inspectable after the fact.
- **No "Urgent alert" path** in v1. Everything lands in the on-hub feed; there is no
  email/push blast that a wrong autonomous decision could fire. This keeps the blast
  radius of a bad tag to "an odd card in a feed," not "a false alarm to the firm."

> If, after running, we find autonomy is too loose for one high-stakes theme (e.g.
> enforcement actions), the smallest fix is a per-theme "confidence floor," not a
> human queue. Noted, not built.

---

## 4. Different for each person

Identity and department resolution already exist — we reuse them.

```
Hub user logs in (Azure AD)
  → hub knows their email via /api/me
  → resolve email → canonical department        (staff-directory's resolver:
                                                  email_overrides → aliases → fuzzy)
  → load that department's interest profile      (departments.yaml)
  → return only items whose tags match           (matcher)
  → render two tabs: Authorities | Journals
```

- **Routing targets = the canonical departments in `staff-directory/departments.json`**
  (Management, Audit & Assurance, Taxation, ICAS, Technology, Funds, Payroll, …), with
  sub-departments where they matter (Taxation → **VAT** / Transfer Pricing / GP / MP;
  ICAS → Compliance / Licensing / Internal Audit / Assurance & Risk).
- Each department (and, where defined, sub-department) has an **interest profile**: the
  set of topic tags it receives. Defined in [departments.yaml](departments.yaml).
- The resolver code "may not be up to date" (per owner) — the `email_overrides` /
  `aliases` in `departments.json` need a refresh pass, but the **mechanism and the
  canonical department list are the contract** we build on.
- This mirrors how the Performance page already self-scopes by identity — the pattern
  is proven in the hub.

---

## 5. Context-level routing (sort by content, not URL)

The whole point. An item's destination is decided by the **topic tags the AI assigns
after reading the article text**, matched against each department's profile.

- **One authority → many departments.** A CySEC publication is tagged by *what it is
  about*: an AML circular → Compliance; a fund-licensing directive → Funds + Licensing;
  a crypto/CASP rule → Licensing (+ Technology). Same source, different destinations.
- **CySEC has many sections — handled carefully:**
  - Each relevant CySEC **section** (Announcements, Circulars, Consultation Papers,
    Policy Statements, Directives, Decisions/Enforcement, Warnings) is collected as its
    own target so we neither miss content nor over-collect.
  - A section maps to the **`type` tag** (Circular vs Consultation vs Enforcement),
    **not** to a department. Department routing comes only from the content themes.
  - No item is ever routed on "it is from CySEC." (D-028: a shared **theme** is
    required; source/jurisdiction alone never matches.)
- **Two source categories change weight, not routing:**
  - **Authority** items can reach any urgency level (real obligations).
  - **Journal** items are **capped** (never top urgency), filtered harder, and default
    lower. Awareness, not compliance.
  - **Cross-category dedup:** when a journal reports on an authority action already
    collected from the primary source, prefer the authority item and suppress the
    journal echo, so a department does not see the same event twice.

Tag axes (full definitions in [taxonomy.md](taxonomy.md)):

- **Theme** — what it is about (routes to departments). Tax/VAT, audit standards, IFRS,
  AML, licensing, funds, ICT/cyber, employment, company law, …
- **Jurisdiction** — Cyprus / EU / International (Cyprus prioritised).
- **Type** — legislation, guidelines/standards, consultation, circular, enforcement,
  report, news/commentary.
- **Source category** — authority / journal (drives the two on-page sections + weight).

---

## 6. Component checklist — status

| # | Deliverable | Status |
|---|---|---|
| 1 | **Treppides taxonomy** ([taxonomy.md](taxonomy.md)) — 25 themes incl. `payments` | ✅ Built |
| 2 | **Department interest map** ([departments.yaml](departments.yaml)) | ✅ Built (Management/KT HK deferred) |
| 3 | **Source register** ([sources.md](sources.md)) — authorities + journals, CySEC sections | ✅ Built |
| 4 | Collectors — 15 RSS + 4 scrapers (CySEC/Tax Dept/CBC/Registrar); generic `html_list` scraper; dedup + health checks | ✅ Built (19 sources) |
| 5 | Triage against the taxonomy, autonomous, article-body fetch, low-confidence → archived, EN/EL only | ✅ Built |
| 6 | Deterministic matcher: themes → department profiles, `matched_on`, journal cap + dedup | ✅ Built |
| 7 | Store: SQLite items + tags + routes + per-source high-water mark; additive migrations | ✅ Built |
| 8 | FastAPI service: `/api/newsletter`, `/api/departments`, `/api/sources`, `/api/items` | ✅ Built |
| 9 | Web page — department view (2 tabs) + Explore (search, source filter, cross-department), sort by date/urgency | ✅ Built (standalone; hub styling TBD) |
| — | Logging (rotating) + nightly pipeline orchestrator (disabled by default) + scheduler script | ✅ Built |
| 10 | nginx route + systemd unit + enable scheduled collection | 🔲 Pending (hub-integration) |
| 11 | Department resolution from `staff-directory` `/api/me` (replace the dev dropdown) | 🔲 Pending (hub-integration) |

---

## 7. Data flow (end to end)

```
[sources.md]                     [taxonomy.md]        [departments.yaml]
   sources          collect         triage               match                 hub
 authority/journal ─────────▶  items ──────▶ tagged items ──────▶ per-dept routes ──▶ /api/newsletter
   (+ CySEC sections)   dedup     (SQLite)    (theme/juris/type,     (shared theme;      (scoped to the
                        health              confidence, category)   journal cap+dedup)   caller's dept,
                        check                                                            2 tabs)
        no human gate anywhere in this line — full autonomy
```

---

## 8. Open items / TBD

Resolved during build: scrapers built (CySEC/Tax Dept/CBC/Registrar); model chosen
(kie.ai gemini-3-5-flash, swappable via `src/llm.py`); source categories set;
`payments` theme added; EN/EL language gate added.

Still open:

- **Hub integration** (§10 F2) — the main remaining work: resolve the caller's
  department from `staff-directory` `/api/me`, mount in the hub, gate by tier, nginx
  + enable the nightly schedule.
- **`departments.json` refresh** — verify `email_overrides` / `aliases` against the
  live Azure roster before trusting department resolution.
- **JS-rendered sources** — MOKAS, ICPAC, Cyprus DPA, EUR-Lex, and CySEC's
  Consultation Papers / Board & Court Decisions / Administrative Sanctions / Warnings
  need a headless browser (Playwright) or an API. Deferred; a decision to add
  Playwright would unlock all of them at once.
- **Deferred profiles** — **Management** (firm-wide digest) and **KT HK** — add once
  core feeds are signed off.
- **CBC noise** — CBC has no topic filter; its statistics skew `economic-general`
  (routes only to Administration). Optionally narrow later.

---

## 9. Explicitly out of scope (v1)

- Human review / editorial approval (by design — full autonomy).
- Email / push / urgent-alert delivery (on-hub feed only).
- Per-employee custom subscriptions (department default only; individual opt-in is a
  later enhancement).
- Client-facing / white-label output (this is internal-only).
- Management and KT HK department profiles (deferred).

---

## 10. Development approach (phased)

Build the whole pipeline **standalone and demoable first**, with a department selector
standing in for identity. Integrate into the hub only at the end (Phase F). Each phase
is independently testable; do not start the next until the current one is proven.

Guiding order: **prove the engine on easy (RSS) sources before taking on the hard
(scraper) ones**, and prove routing quality before building any UI.

| Phase | Goal | Done when |
|---|---|---|
| **A. Scaffold** | New standalone service folder (FastAPI + SQLite), reusing the Finalogic module patterns (collectors / triage / matching / store). Finalise the three config docs. | Service runs locally; `taxonomy.md`, `departments.yaml`, `sources.md` locked. |
| **B. Collect (RSS only)** | Collectors for the RSS-available authorities (EU bodies, IFRS/IASB, OECD, ICPAC) + 1–2 journals. Verify each feed live first; dedup; per-source health checks. | Items land in SQLite; a re-run inserts nothing (dedup proven); zero-item source fails loudly. |
| **C. Triage** | Adapt the triage engine to inject `taxonomy.md`; tag each item (theme/jurisdiction/type + confidence); autonomous; low-confidence/`other` archived. | A sample triages with in-taxonomy tags; a spot-check of tax/AML/ICT items looks right. |
| **D. Match / route** | Deterministic matcher: item themes → `departments.yaml`; store per-department routes; journal cap + cross-category dedup. | A VAT item lands in **Taxation/VAT** and **not** Technology; a CySEC-style AML item fans out to Compliance, not everyone. |
| **E. Standalone UI** | Self-contained page with a **department dropdown** (dev stand-in for identity) and two tabs (Authorities / Journals), reading `GET /api/newsletter?department=…`. Matches hub styling so the later merge is trivial. | Pick "Taxation → VAT" → see only VAT-relevant items, split into the two sections. This is the demoable component. |
| **F1. Scrapers** | CySEC (per section), CBC, Tax Department, Registrar. Built after RSS is proven; each verified live. | Cyprus authority items flow through the same triage/match unchanged. |
| **F2. Hub integration** | Replace the dropdown with identity: `/api/me` email → `staff-directory` resolver → department. Add to hub sidebar/home page, tier gate, nginx route, systemd unit, scheduled collection. | A logged-in user sees their own department's feed on the hub with no selector. |

Phases A–E + F1 are the **standalone component**. F2 is the hub merge — deliberately last,
so identity/auth work never blocks proving the feed itself.

**To start, two decisions are needed:**
1. **Triage model/provider** — inherit the Finalogic swappable `llm.py` (one HTTP call);
   pick the model and supply an API key.
2. **Dev runtime** — run the standalone component locally during A–E, or stand it up on
   the server behind its own port from the start.
