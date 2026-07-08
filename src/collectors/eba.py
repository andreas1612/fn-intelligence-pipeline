from src.collectors.base import fetch_rss
from src.sources import SOURCES

SOURCE_NAME = "EBA"


def collect() -> list[dict]:
    feed_url = SOURCES[SOURCE_NAME]["feed_url"]
    return fetch_rss(SOURCE_NAME, feed_url)
