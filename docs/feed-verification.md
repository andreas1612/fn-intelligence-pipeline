# Wave 1 Feed Verification

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

## Summary

| Source | Result | Feed URL |
|---|---|---|
| EBA | Verified | `https://www.eba.europa.eu/news-press/news/rss.xml` |
| ESMA | Verified | `https://www.esma.europa.eu/rss.xml` |
| ENISA | No working feed | none available; owner decision needed |
| CERT-EU | Verified | `https://cert.europa.eu/publications/security-advisories-rss` |
| CISA KEV | Verified | `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` |

4 of 5 Wave 1 sources have a verified working feed. ENISA is blocked; see decision needed above.
