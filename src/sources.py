"""Verified Wave 1 feed URLs. See docs/feed-verification.md for evidence and dates.

Update this file, not the individual collectors, when a feed URL changes.
"""

SOURCES = {
    "EBA": {
        "feed_url": "https://www.eba.europa.eu/news-press/news/rss.xml",
        "feed_type": "rss",
    },
    "ESMA": {
        "feed_url": "https://www.esma.europa.eu/rss.xml",
        "feed_type": "rss",
    },
    "CERT-EU": {
        "feed_url": "https://cert.europa.eu/publications/security-advisories-rss",
        "feed_type": "rss",
    },
    "CISA_KEV": {
        "feed_url": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        "feed_type": "json",
    },
}
