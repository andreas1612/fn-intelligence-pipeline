"""Run all collectors, store items, and report per-source health."""

import sys

from src import db
from src.collectors import cert_eu, cisa_kev, eba, ec_digital, edpb, eiopa, esma, ncsc_uk
from src.collectors.base import logger

COLLECTORS = {
    "EBA": eba.collect,
    "ESMA": esma.collect,
    "CERT-EU": cert_eu.collect,
    "CISA_KEV": cisa_kev.collect,
    "EIOPA": eiopa.collect,
    "EC_DIGITAL": ec_digital.collect,
    "EDPB": edpb.collect,
    "NCSC_UK": ncsc_uk.collect,
}


def run() -> int:
    conn = db.connect()
    zero_item_sources = []
    failed_sources = []

    for source, collect in COLLECTORS.items():
        try:
            items = collect()
        except Exception as exc:
            logger.error("source=%s status=FAILED error=%s", source, exc)
            failed_sources.append(source)
            continue

        new_count = sum(1 for item in items if db.insert_item(conn, item))
        logger.info(
            "source=%s items_fetched=%d items_new=%d",
            source,
            len(items),
            new_count,
        )
        if len(items) == 0:
            zero_item_sources.append(source)

    conn.close()

    if zero_item_sources:
        logger.warning("HEALTH CHECK: zero items fetched from: %s", ", ".join(zero_item_sources))
    if failed_sources:
        logger.error("HEALTH CHECK: collector failures from: %s", ", ".join(failed_sources))

    return 1 if (zero_item_sources or failed_sources) else 0


if __name__ == "__main__":
    sys.exit(run())
