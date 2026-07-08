import requests

from src.collectors.base import now_iso
from src.sources import SOURCES

SOURCE_NAME = "CISA_KEV"
NVD_URL_TEMPLATE = "https://nvd.nist.gov/vuln/detail/{cve_id}"


def collect() -> list[dict]:
    feed_url = SOURCES[SOURCE_NAME]["feed_url"]
    response = requests.get(feed_url, timeout=30)
    response.raise_for_status()
    data = response.json()

    retrieved_at = now_iso()
    items = []
    for vuln in data["vulnerabilities"]:
        cve_id = vuln["cveID"]
        items.append(
            {
                "source": SOURCE_NAME,
                "title": f"{cve_id}: {vuln['vulnerabilityName']}",
                "url": NVD_URL_TEMPLATE.format(cve_id=cve_id),
                "published_at": vuln.get("dateAdded"),
                "retrieved_at": retrieved_at,
                "summary": vuln.get("shortDescription"),
            }
        )
    return items
