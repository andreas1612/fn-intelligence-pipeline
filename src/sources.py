"""Verified feed URLs. See docs/feed-verification.md for evidence and dates.

Update this file, not the individual collectors, when a feed URL changes.
"""

SOURCES = {
    # Wave 1

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
    # Wave 2 expansion (Phase 6, D-029)
    "EIOPA": {
        # Drupal node feed advertised by the RSS link on eiopa.europa.eu/media/news_en.
        # The node id is the site's internal key: recheck if the feed starts 404ing.
        "feed_url": "https://www.eiopa.europa.eu/node/4816/rss_en",
        "feed_type": "rss",
    },
    "EC_DIGITAL": {
        # Shaping Europe's Digital Future, site-wide. No AI-topic feed exists, so AI
        # items are separated by tagging at triage, not at collection.
        "feed_url": "https://digital-strategy.ec.europa.eu/en/rss.xml",
        "feed_type": "rss",
    },
    "EDPB": {
        # Site-wide feed: carries news alongside the occasional non-news page.
        "feed_url": "https://www.edpb.europa.eu/rss.xml",
        "feed_type": "rss",
    },
}
