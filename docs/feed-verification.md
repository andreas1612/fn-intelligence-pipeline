# Feed Verification

Every feed URL is verified against the live site before its collector is coded. The
source register asserts no exact URLs on purpose. This file is the evidence.

Sections are grouped by build wave. Wave 1 was verified on 2026-07-07; the Wave 2
expansion (Phase 6, D-029) is verified per source as each collector is built.

---

# Wave 1 (Phase 2)

Verification date: 2026-07-07. Verified by fetching each URL directly and checking the response.

## EBA

**Status:** Verified.
**URL:** `https://www.eba.europa.eu/news-press/news/rss.xml`
**Format:** RSS 2.0.
**Evidence:** Returns valid RSS with channel title "European Banking Authority". Items include publication dates and links to `eba.europa.eu/publications-and-media/press-releases/...`. Most recent item dated 2026-07-07 at time of check.
**Note:** The EBA site has restructured its news pages under `/publications-and-media/press-releases/`, but the legacy `/news-press/news/rss.xml` feed path still resolves and serves current items. Recheck this path periodically in case it is retired.

## ESMA

**Status:** Verified.
**URL:** `https://www.esma.europa.eu/rss.xml`
**Format:** RSS 2.0.
**Evidence:** Returns valid RSS with channel title "European Securities and Markets Authority". Items include current dated entries linking to `esma.europa.eu/press-news/esma-news/...`.
**Note:** A source-specific feed at `https://www.esma.europa.eu/press-news/esma-news/rss.xml` did not return distinct XML content in testing. Use the site-wide `rss.xml` path above.

## ENISA

**Status:** No working feed. Stop work on this source per collector build rules.
**Evidence:**
- `https://www.enisa.europa.eu/rss-feeds` returns HTTP 403.
- `https://www.enisa.europa.eu/rss-feeds-discontinued-new-subscription-mechanism-coming-soon` states: "RSS feeds have been discontinued. A new subscription mechanism is currently being developed to provide a more efficient and user-friendly way to stay updated." No date given for when a replacement will ship.
- Legacy feed path `https://www.enisa.europa.eu/media/news-items/news-wires/RSS` returns HTTP 404.
- `https://www.enisa.europa.eu/news/rss.xml` returns HTTP 404.
- The only current subscription mechanism is an email alert signup (`/alertservice`), not a feed or API.
**Decision needed:** ENISA has no RSS or API endpoint to collect from today. Options: (a) drop ENISA from the Wave 1 build until the agency ships its replacement subscription mechanism, and flag it in ROADMAP.md as blocked, or (b) build ENISA as a Wave 2/Phase 5 scraper against `/media/news-items/news-wires`, which changes it from an RSS source to a scrape source and is out of scope for "Wave 1: RSS and API only" per the source register. No unofficial mirror (e.g. third-party RSS reader re-publishing ENISA content) will be substituted, per project rules. Flagging for owner decision rather than assuming.

## CERT-EU

**Status:** Verified.
**URL:** `https://cert.europa.eu/publications/security-advisories-rss`
**Format:** RSS 2.0.
**Evidence:** Returns valid RSS with channel title "Latest publications of type Security Advisories". Items include entries such as "2026-008: Critical vulnerabilities in Ivanti Sentry" linking to `cert.europa.eu/publications/security-advisories/2026-008/`.
**Note:** This feed covers Security Advisories only. CERT-EU also publishes other content types (e.g. threat intelligence reports) under separate URL paths; out of scope for Wave 1, which targets advisories per the source register ("actionable advisories, urgent-alert exerciser").

## CISA KEV catalogue

**Status:** Verified.
**URL:** `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`
**Format:** JSON API.
**Evidence:** Returns valid JSON with keys `title`, `catalogVersion`, `dateReleased`, `count`, `vulnerabilities`. At time of check: `catalogVersion` 2026.07.01, `count` 1631.
**Note:** The CISA web pages themselves (e.g. `cisa.gov/known-exploited-vulnerabilities-catalog`) returned HTTP 403 to automated fetch, but the JSON feed file under `/sites/default/files/feeds/` is directly reachable and does not require the HTML page. The collector should hit the JSON URL directly, not the HTML page.
**Per-item URL mapping:** KEV entries have no per-item article URL field (fields are `cveID`, `vendorProject`, `product`, `vulnerabilityName`, `dateAdded`, `shortDescription`, `requiredAction`, `dueDate`, `knownRansomwareCampaignUse`, `notes`, `cwes`). By owner decision, the stored `url` for each item is the per-CVE NVD record page, pattern `https://nvd.nist.gov/vuln/detail/{cveID}`. Verified live: `https://nvd.nist.gov/vuln/detail/CVE-2026-45659` resolves and shows matching CVE detail. The `source` column stays `CISA_KEV`, the register-named source; NVD is only the per-item link target.

## Wave 1 summary

| Source | Result | Feed URL |
|---|---|---|
| EBA | Verified | `https://www.eba.europa.eu/news-press/news/rss.xml` |
| ESMA | Verified | `https://www.esma.europa.eu/rss.xml` |
| ENISA | No working feed | none available; owner decision needed |
| CERT-EU | Verified | `https://cert.europa.eu/publications/security-advisories-rss` |
| CISA KEV | Verified | `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` |

4 of 5 Wave 1 sources have a verified working feed. ENISA is blocked; see decision needed above.

---

# Wave 2 expansion (Phase 6, D-029)

Verified per source, immediately before that source's collector was coded. Method: fetch
the candidate URL directly, check the HTTP status and content type, parse with feedparser,
and record the channel title, entry count, and newest items. Where a guessed path failed,
the feed URL was taken from the publisher's own markup (the RSS link on its news page),
never from a search engine or a third-party feed directory.

## EIOPA

**Status:** Verified.
**Verification date:** 2026-07-21.
**URL:** `https://www.eiopa.europa.eu/node/4816/rss_en`
**Format:** RSS 2.0 (`Content-Type: application/rss+xml; charset=utf-8`, feedparser `rss20`, `bozo=False`).
**Sample item count:** 30 entries, spanning 2026-03-30 to 2026-07-16 at time of check.
**Evidence:** Channel title `European Insurance and Occupational Pensions Authority | News`. Entries carry `published` dates and per-item links under `eiopa.europa.eu/...`, for example:
- 2026-07-16 "EIOPA publishes factsheet on European (re)insurers' exposures to private credit and private equity"
- 2026-07-15 "EIOPA completes Solvency II Review mandate with final guidelines and draft technical standards"
- 2026-07-07 "The ESAs support ESRB warning on systemic cyber risks from frontier AI models"

**How the URL was found:** The obvious Drupal paths all returned HTTP 404 against a live site: `https://www.eiopa.europa.eu/rss.xml`, `https://www.eiopa.europa.eu/news/rss.xml`, and `https://www.eiopa.europa.eu/media/news/rss.xml`. The feed URL above is the one EIOPA advertises itself, in the "RSS" anchor on its own news page `https://www.eiopa.europa.eu/media/news_en`. No path was guessed into use.

**Note (fragility):** `node/4816` is the site's internal Drupal node id, not a stable public path, so it could change if EIOPA rebuilds its news section. The failure mode is a 404 and a zero-item or failed run, which the health check surfaces (D-009) rather than passing silently. If it breaks, re-read the RSS link on `/media/news_en` rather than guessing a replacement.

**Collector result (2026-07-21):** First run fetched 30 items, inserted 30. Immediate re-run fetched 30, inserted 0, confirming content-hash dedup. No null titles, URLs, or publication dates. No duplicate content hashes anywhere in the database.

**Taxonomy note:** EIOPA is the source that activates the Insurance sector tag (D-029), which no existing source feeds. No taxonomy change was needed.

## European Commission, Shaping Europe's Digital Future / AI

**Status:** Verified.
**Verification date:** 2026-07-21.
**URL:** `https://digital-strategy.ec.europa.eu/en/rss.xml`
**Format:** RSS 2.0 (`Content-Type: application/rss+xml; charset=utf-8`, feedparser `rss20`, `bozo=False`).
**Sample item count:** 10 entries, newest 2026-07-20 at time of check.
**Evidence:** Channel title `Shaping Europe's digital future`, which is the register's named source. Entries link to `digital-strategy.ec.europa.eu/en/...`, for example:
- 2026-07-20 "Commission publishes guidelines on transparency obligations for providers and deployers of certain AI systems"
- 2026-07-20 "Commission fines AliExpress EUR 550 million for breaching the Digital Services Act"
- 2026-07-20 "Guidelines on transparency obligations for providers and deployers of AI systems"

**How the URL was found:** Unlike EIOPA, this site advertises no RSS link in its own markup: the news listing is rendered client side from a Solr search, and a raw scan of `/en/news` and `/en/policies/artificial-intelligence` found zero occurrences of "rss", "feed", or "atom". The URL above was confirmed by request against the official domain, and accepted only because it returns a well-formed RSS 2.0 document whose channel title matches the named source and whose items link back to that same domain. `https://digital-strategy.ec.europa.eu/rss.xml` returns byte-identical content; the `/en/` path is used to pin the language explicitly, since the site serves 24 languages.

**Note (feed is site-wide, not AI-only):** No AI-topic feed exists. `/en/policies/artificial-intelligence/rss.xml` and `/en/news/rss.xml` both return HTTP 200 with an HTML page and zero entries, so neither is a feed. The site-wide feed mixes news, events, and library items, so events and non-AI digital-policy items arrive alongside AI Act content. This is the same situation as ESMA's site-wide `rss.xml` and is handled the same way: separation happens through taxonomy tagging at triage, not at collection. Triage cost is about $0.002 per item, so the extra volume is immaterial.

**Note (short window):** The feed carries only 10 entries, a narrower window than EIOPA's 30. Daily collection covers it; a multi-day gap in collection could miss items.

**Collector result (2026-07-21):** First run fetched 10 items, inserted 10. Immediate re-run fetched 10, inserted 0, confirming content-hash dedup.

## EDPB

**Status:** Verified.
**Verification date:** 2026-07-21.
**URL:** `https://www.edpb.europa.eu/rss.xml`
**Format:** RSS 2.0 (`Content-Type: application/rss+xml; charset=utf-8`, feedparser `rss20`, `bozo=False`).
**Sample item count:** 10 entries, newest 2026-07-17 at time of check.
**Evidence:** Channel title `European Data Protection Board`. Entries link to `edpb.europa.eu/...`, for example:
- 2026-07-17 "EDPB calls for legal basis for cross-regulatory information sharing"
- 2026-07-14 "EDPB requires Belgian DPA to handle the merits of NOYB cookie banner complaint"
- 2026-07-08 "EDPB sheds light on anonymisation and web scraping for generative AI and adopts final version of guidelines"

**How the URL was found:** As with the Commission site, EDPB advertises no feed in its own markup: `/news/news_en` is server rendered but a raw scan found zero occurrences of "rss", "feed", or "atom". The URL above was confirmed by request against the official domain and returns well-formed RSS 2.0 with the matching channel title. Two other candidates were tried and rejected on evidence: `https://www.edpb.europa.eu/en/rss.xml` returns HTTP 404, and the EIOPA-style `https://www.edpb.europa.eu/node/572/rss_en` also returns HTTP 404, so the node-feed route is not general across europa.eu Drupal sites.

**Note (feed is site-wide):** The feed is not news-only. One of the ten sample entries was an "Acknowledgement of receipt" page under `/contact/`, so occasional non-news pages arrive. Triage tags and levels them like anything else, and low-value items land at Low and fall below most client `min_level` settings. Watch this at review: if administrative pages recur, the fix is a title or URL-path filter in the collector, not a taxonomy change.

**Note (short window):** 10 entries, so daily collection matters, as with the Commission feed.

**Collector result (2026-07-21):** First run fetched 10 items, inserted 10. Immediate re-run fetched 10, inserted 0, confirming content-hash dedup.

## NCSC UK

**Status:** Verified.
**Verification date:** 2026-07-21.
**URL:** `https://www.ncsc.gov.uk/api/1/services/v1/news-rss-feed.xml`
**Format:** RSS 2.0 (`Content-Type: application/rss+xml; charset=utf-8`, feedparser `rss20`, `bozo=False`).
**Sample item count:** 20 entries, newest 2026-07-13 at time of check.
**Evidence:** Channel title `News Feed`. Entries link to `ncsc.gov.uk/news/...`, for example:
- 2026-07-13 "UK and Allies urge critical sectors to improve defences against Russian intelligence targeting"
- 2026-06-18 "Alert: NCSC issues advice following global targeting of Fortinet firewalls and VPN gateways"
- 2026-06-22 "The AI shift in cyber risk: why leaders must act now"

**How the URL was found:** NCSC publishes a feeds page at `https://www.ncsc.gov.uk/information/rss-feeds`, linked from its own site header. That page lists five official feeds, all under `/api/1/services/v1/`: All, Guidance, News, Blog posts, and Threat Reports. The URL above is taken directly from that page.

**Why the News feed and not the others:** This follows the CERT-EU precedent, where the collector deliberately takes the Security Advisories feed and other content types are out of scope. The News feed is NCSC's alerts and advisories stream, which is the actionable content D-029 asked for. The other four were checked before choosing:

- **All** (`all-rss-feed.xml`): despite the name it is not everything. Its 20 entries were 13 blog posts and 7 news items, with no guidance and no reports. Blog-heavy commentary, so rejected.
- **Guidance** (`guidance-rss-feed.xml`): valid, but slow moving. Newest entry 2026-03-19, four months old at time of check.
- **Threat Reports** (`report-rss-feed.xml`): valid, but the newest entry was 2025-05-07 and the feed reaches back to 2023. Reference material, not a routine stream.
- **Blog posts** (`blog-post-rss-feed.xml`): commentary, not intelligence.

Guidance and Threat Reports remain candidates if a reviewer wants the reference material. Both are stale enough that adding them now would mostly import an ageing backlog, so they are left out rather than assumed in.

**Jurisdiction note:** NCSC UK is the first routine International-jurisdiction source (D-029). This is what exercises D-028: International items cannot match on jurisdiction alone, so they reach a client only on a shared sector or theme. No taxonomy change was needed, since International already exists.

**Collector result (2026-07-21):** First run fetched 20 items, inserted 20. Immediate re-run fetched 20, inserted 0, confirming content-hash dedup.

## Wave 2 expansion summary

| Source | Result | Feed URL |
|---|---|---|
| EIOPA | Verified 2026-07-21 | `https://www.eiopa.europa.eu/node/4816/rss_en` |
| European Commission (AI) | Verified 2026-07-21 | `https://digital-strategy.ec.europa.eu/en/rss.xml` |
| EDPB | Verified 2026-07-21 | `https://www.edpb.europa.eu/rss.xml` |
| NCSC UK | Verified 2026-07-21 | `https://www.ncsc.gov.uk/api/1/services/v1/news-rss-feed.xml` |
| ECB / SSM | Not yet verified | TBD |

---

# Observed source outages

Recorded when a previously verified feed fails, so a transient upstream outage is not
mistaken later for a wrong URL.

- **EBA, 2026-07-21**: `https://www.eba.europa.eu/news-press/news/rss.xml` returned HTTP 502 with an "EBA | Maintenance" HTML page instead of the feed. The collector failed loudly and `src/run.py` exited non-zero, per D-009. The URL is unchanged and is not re-verified as broken on this basis. Recovered the same day: a later run in the same session fetched 10 items from the same URL with no code change, confirming a transient outage rather than a retired feed. Note that `fetch_rss` reports this as a parse failure, because feedparser fetches the URL itself and does not check the HTTP status; the run still fails, which is the requirement.
