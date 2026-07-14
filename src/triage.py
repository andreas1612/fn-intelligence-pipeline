"""Triage: classify, score, and summarise untriaged items via the Claude API.

One API call per item (D-016). Tags come only from docs/taxonomy-v1.0.md and
levels only from docs/scoring-criteria.md, both read at runtime and injected
into src/triage_prompt.md. Model output is validated before it is written.
Raw item columns are never altered.

Run with: python -m src.triage [--limit N] [--dry-run]
"""

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src import db, migrate
from src.collectors.base import logger

# Model and request settings (D-015, D-016). One call per item, no batch API,
# no prompt caching, no KEV pre-filter.
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1500
TEMPERATURE = 0

# Pricing in USD per million tokens for claude-sonnet-4-6.
# Verified 2026-07-09 against the published Anthropic rates.
INPUT_USD_PER_MTOK = 3.00
OUTPUT_USD_PER_MTOK = 15.00

# Fetch settings.
FETCH_CHAR_CAP = 20000
FETCH_TIMEOUT = 20
USER_AGENT = "Finalogic intelligence pipeline (regulatory monitoring; info@finalogic.com)"
STRIP_TAGS = ("script", "style", "nav", "header", "footer", "aside", "noscript", "form")

# Eligibility cutoff for CISA KEV only (D-017). Verified against stored
# retrieved_at values, which carry a +00:00 suffix, so the prefix compares
# correctly as a string.
KEV_SOURCE = "CISA_KEV"
KEV_CUTOFF = "2026-07-08T00:00:00"

LEVELS = ("Urgent", "High", "Standard", "Low")
DISCARD_RULES = ("AD-2", "AD-3")
CONFIDENCE = ("high", "medium", "low")

# Every rules_applied entry must be a rule ID from scoring-criteria.md (D-019).
# Free text is a validation failure, not a stylistic preference.
#
# F rules are excluded here on purpose (D-021 defect 2). The prompt says flag
# rules belong in flag_rules and rules_applied holds only the rules that
# determined the outcome. The old pattern accepted F- in both, so prompt and
# validator disagreed and the model put F-2 in rules_applied on 12 of 13
# flagged items. The two fields are now validated separately.
RULE_ID_RE = re.compile(r"^(AD|U|H|W|S|L)-\d+$")
FLAG_RULE_ID_RE = re.compile(r"^F-\d+$")

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "src" / "triage_prompt.md"
TAXONOMY_PATH = ROOT / "docs" / "taxonomy-v1.0.md"
SCORING_PATH = ROOT / "docs" / "scoring-criteria.md"
RUN_LOG_PATH = ROOT / "logs" / "triage_runs.jsonl"

ELIGIBLE_SQL = f"""
SELECT id, source, title, url, published_at, summary
FROM items
WHERE triaged_at IS NULL
AND (source != '{KEV_SOURCE}' OR retrieved_at >= '{KEV_CUTOFF}')
ORDER BY id
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Prompt and controlled vocabulary -------------------------------------


def load_prompt_template() -> str:
    """Read the approved template and strip the header above the --- separator."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"{PROMPT_PATH} has no --- separator")
    return parts[1].lstrip("\n")


@dataclass(frozen=True)
class Taxonomy:
    themes: frozenset[str]
    sectors: frozenset[str]
    jurisdictions: frozenset[str]
    types: frozenset[str]


def _tags_in_section(text: str, start_heading: str, end_heading: str) -> frozenset[str]:
    start = text.index(start_heading)
    end = text.index(end_heading, start)
    section = text[start:end]
    return frozenset(re.findall(r"^- \*\*(.+?)\*\*", section, flags=re.MULTILINE))


def load_taxonomy(text: str) -> Taxonomy:
    """Extract the controlled tag vocabulary from taxonomy-v1.0.md.

    Tags are the bolded entries in sections 3 to 6. Parsed rather than copied
    so this module never holds a second copy of the locked document (D-016).
    """
    taxonomy = Taxonomy(
        themes=_tags_in_section(text, "## 3. Theme tags", "## 4. Sector tags"),
        sectors=_tags_in_section(text, "## 4. Sector tags", "## 5. Jurisdiction tags"),
        jurisdictions=_tags_in_section(text, "## 5. Jurisdiction tags", "## 6. Type tags"),
        types=_tags_in_section(text, "## 6. Type tags", "## 7. Tagging rules"),
    )
    expected = {"themes": 15, "sectors": 5, "jurisdictions": 3, "types": 7}
    for group, count in expected.items():
        actual = len(getattr(taxonomy, group))
        if actual != count:
            raise ValueError(
                f"taxonomy parse mismatch: {group} has {actual} tags, document declares {count}"
            )
    return taxonomy


def fill_placeholders(template: str, values: dict[str, str]) -> str:
    """Substitute {{PLACEHOLDER}} tokens in one pass.

    A single pass means injected document or item text is never rescanned for
    further placeholders.
    """
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            missing.append(key)
            return match.group(0)
        return values[key]

    filled = re.sub(r"\{\{([A-Z0-9_]+)\}\}", replace, template)
    if missing:
        raise KeyError(f"prompt template has unfilled placeholders: {sorted(set(missing))}")
    return filled


# --- Fetch ----------------------------------------------------------------


def strip_html(html: str | None) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def fetch_page(url: str) -> tuple[str, str]:
    """Fetch and extract readable text. Returns (text, fetch_status).

    Never raises. On any failure the caller proceeds on title plus feed
    snippet with F-3 flagged (D-016).
    """
    try:
        response = requests.get(
            url, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
    except requests.Timeout:
        return "", "timeout"
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "unknown"
        return "", f"http_{code}"
    except requests.RequestException as exc:
        return "", f"fetch_error_{type(exc).__name__}"

    try:
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:  # noqa: BLE001 - malformed markup must not skip the item
        return "", f"parse_error_{type(exc).__name__}"

    for tag in soup(list(STRIP_TAGS)):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    if not text.strip():
        return "", "empty_content"
    return text[:FETCH_CHAR_CAP], "ok"


# --- Validation -----------------------------------------------------------


def _check_tag_list(
    value: object, name: str, allowed: frozenset[str], low: int, high: int
) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return [f"{name} must be a list of strings, got {value!r}"]
    errors = []
    if not low <= len(value) <= high:
        errors.append(f"{name} must have {low} to {high} entries, got {len(value)}")
    for tag in value:
        if tag not in allowed:
            errors.append(f"{name} entry {tag!r} is not a tag in the taxonomy")
    return errors


def validate(result: object, taxonomy: Taxonomy) -> list[str]:
    """Return a list of validation errors. Empty list means the result is usable."""
    if not isinstance(result, dict):
        return [f"response must be a JSON object, got {type(result).__name__}"]

    errors: list[str] = []

    discard = result.get("auto_discard")
    if discard is not None and discard not in DISCARD_RULES:
        errors.append(f"auto_discard must be null, 'AD-2', or 'AD-3', got {discard!r}")

    errors += _check_tag_list(result.get("theme_tags"), "theme_tags", taxonomy.themes, 1, 3)
    errors += _check_tag_list(result.get("sector_tags"), "sector_tags", taxonomy.sectors, 0, 2)

    jurisdiction = result.get("jurisdiction")
    if not isinstance(jurisdiction, str) or jurisdiction not in taxonomy.jurisdictions:
        errors.append(f"jurisdiction must be exactly one taxonomy tag, got {jurisdiction!r}")

    type_tag = result.get("type")
    if not isinstance(type_tag, str) or type_tag not in taxonomy.types:
        errors.append(f"type must be exactly one taxonomy tag, got {type_tag!r}")

    level = result.get("level")
    if level is not None and level not in LEVELS:
        errors.append(f"level must be one of {LEVELS} or null, got {level!r}")
    if discard is not None and level is not None:
        errors.append(f"level must be null when auto_discard is set, got {level!r}")
    if discard is None and level is None:
        errors.append("level must be set when auto_discard is null")

    rules = result.get("rules_applied")
    if not isinstance(rules, list) or not all(isinstance(r, str) for r in rules):
        errors.append(f"rules_applied must be a list of strings, got {rules!r}")
    elif not rules:
        errors.append("rules_applied must name every rule applied, got an empty list")
    else:
        for rule in rules:
            if not RULE_ID_RE.match(rule):
                errors.append(
                    f"rules_applied entry {rule!r} is not a level, weighting, or discard "
                    "rule ID. Use only bare IDs such as AD-2, U-1, H-3, S-1, L-1, W-2. "
                    "Flag rules (F-1 to F-4) belong in flag_rules, not here. No free text, "
                    "no explanation, and no rules you considered and rejected."
                )

    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        errors.append("summary must be a non-empty string")

    flagged = result.get("flagged")
    if not isinstance(flagged, bool):
        errors.append(f"flagged must be true or false, got {flagged!r}")

    flag_rules = result.get("flag_rules")
    if not isinstance(flag_rules, list) or not all(isinstance(r, str) for r in flag_rules):
        errors.append(f"flag_rules must be a list of strings, got {flag_rules!r}")
    else:
        for rule in flag_rules:
            if not FLAG_RULE_ID_RE.match(rule):
                errors.append(
                    f"flag_rules entry {rule!r} is not a flag rule ID. Use only F-1 to "
                    "F-4. Level, weighting, and discard rules belong in rules_applied."
                )
        if flagged is True and not flag_rules:
            errors.append("flag_rules must name the F rule that triggered the flag")
        if flagged is False and flag_rules:
            errors.append(f"flag_rules must be empty when flagged is false, got {flag_rules!r}")

    if not isinstance(result.get("flag_reason"), str):
        errors.append(f"flag_reason must be a string, got {result.get('flag_reason')!r}")

    if result.get("confidence") not in CONFIDENCE:
        errors.append(f"confidence must be one of {CONFIDENCE}, got {result.get('confidence')!r}")

    return errors


def extract_json(raw: str) -> object:
    """Parse the model response. Tolerates a markdown fence, nothing more."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# --- Persistence ----------------------------------------------------------

WRITE_SQL = """
UPDATE items SET
    triaged_at = ?, auto_discard = ?, theme_tags = ?, sector_tags = ?,
    jurisdiction = ?, type = ?, level = ?, rules_applied = ?, ai_summary = ?,
    flagged = ?, flag_rules = ?, flag_reason = ?, confidence = ?,
    fetch_status = ?, model = ?, input_tokens = ?, output_tokens = ?
WHERE id = ?
"""


def write_result(
    conn: sqlite3.Connection,
    item_id: int,
    result: dict,
    fetch_status: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    conn.execute(
        WRITE_SQL,
        (
            now_iso(),
            result.get("auto_discard"),
            json.dumps(result["theme_tags"]),
            json.dumps(result["sector_tags"]),
            result["jurisdiction"],
            result["type"],
            result.get("level"),
            json.dumps(result["rules_applied"]),
            result["summary"],
            1 if result["flagged"] else 0,
            json.dumps(result["flag_rules"]),
            result["flag_reason"],
            result["confidence"],
            fetch_status,
            MODEL,
            input_tokens,
            output_tokens,
            item_id,
        ),
    )
    conn.commit()


INVALID_SQL = """
UPDATE items SET
    triaged_at = ?, flagged = 1, flag_reason = ?, fetch_status = ?,
    model = ?, input_tokens = ?, output_tokens = ?
WHERE id = ?
"""


def write_invalid(
    conn: sqlite3.Connection,
    item_id: int,
    errors: list[str],
    raw: str,
    fetch_status: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Record an item whose model output failed validation twice.

    The spec asks for both the marker 'invalid model output' and the raw
    response in flag_reason. Both are kept in one field, marker first.
    No tags, level, or summary are written: nothing is invented.
    """
    reason = f"invalid model output: {'; '.join(errors)} | raw: {raw[:2000]}"
    conn.execute(
        INVALID_SQL,
        (now_iso(), reason, fetch_status, MODEL, input_tokens, output_tokens, item_id),
    )
    conn.commit()


# --- Run ------------------------------------------------------------------


# Marks each run log line so partial runs are not summed with full ones.
RUN_TYPES = ("pilot", "proof", "full", "re-triage")


@dataclass
class RunReport:
    run_at: str
    run_type: str = "full"
    items_eligible: int = 0
    items_triaged: int = 0
    items_flagged: int = 0
    items_discarded: int = 0
    items_invalid: int = 0
    items_api_error: int = 0
    fetch_failures: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = MODEL
    api_errors: list[str] = field(default_factory=list)

    @property
    def cost_usd(self) -> float:
        input_cost = self.input_tokens / 1_000_000 * INPUT_USD_PER_MTOK
        output_cost = self.output_tokens / 1_000_000 * OUTPUT_USD_PER_MTOK
        return round(input_cost + output_cost, 4)

    def to_json(self) -> dict:
        payload = {k: v for k, v in self.__dict__.items()}
        payload["cost_usd"] = self.cost_usd
        payload["input_usd_per_mtok"] = INPUT_USD_PER_MTOK
        payload["output_usd_per_mtok"] = OUTPUT_USD_PER_MTOK
        return payload


def call_model(client: anthropic.Anthropic, prompt: str) -> tuple[str, int, int]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return text, response.usage.input_tokens, response.usage.output_tokens


def retry_prompt(prompt: str, errors: list[str]) -> str:
    return (
        prompt
        + "\n\n# Correction required\n\n"
        + "Your previous response failed validation:\n"
        + "\n".join(f"- {e}" for e in errors)
        + "\n\nReturn a corrected JSON object only. Use tags exactly as written in "
        "the taxonomy above. Do not invent tags, levels, or rules."
    )


def triage_item(
    client: anthropic.Anthropic | None,
    conn: sqlite3.Connection,
    item: sqlite3.Row,
    template: str,
    taxonomy: Taxonomy,
    taxonomy_text: str,
    scoring_text: str,
    report: RunReport,
    dry_run: bool,
) -> None:
    item_id = item["id"]
    fetched_text, fetch_status = fetch_page(item["url"])
    if fetch_status != "ok":
        report.fetch_failures += 1
        logger.warning("item=%d fetch_status=%s url=%s", item_id, fetch_status, item["url"])

    prompt = fill_placeholders(
        template,
        {
            "TAXONOMY_V1_0": taxonomy_text,
            "SCORING_CRITERIA": scoring_text,
            "SOURCE": item["source"],
            "TITLE": item["title"],
            "URL": item["url"],
            "PUBLISHED_AT": item["published_at"] or "unknown",
            "FEED_SNIPPET": strip_html(item["summary"]) or "(none)",
            "FETCH_CHAR_CAP": str(FETCH_CHAR_CAP),
            "FETCHED_TEXT": fetched_text or "(page text unavailable)",
        },
    )

    if dry_run:
        logger.info(
            "item=%d source=%s fetch_status=%s prompt_chars=%d DRY RUN, no API call",
            item_id,
            item["source"],
            fetch_status,
            len(prompt),
        )
        return

    assert client is not None
    item_input = item_output = 0
    raw = ""
    errors: list[str] = []

    # One call, then at most one retry carrying the validation error.
    for attempt in (1, 2):
        try:
            raw, used_in, used_out = call_model(client, prompt)
        except anthropic.APIError as exc:
            report.items_api_error += 1
            report.api_errors.append(f"item {item_id}: {type(exc).__name__}: {exc}")
            logger.error("item=%d API error, left untriaged for a later run: %s", item_id, exc)
            return

        item_input += used_in
        item_output += used_out
        report.input_tokens += used_in
        report.output_tokens += used_out

        try:
            result = extract_json(raw)
            errors = validate(result, taxonomy)
        except json.JSONDecodeError as exc:
            result, errors = None, [f"response was not valid JSON: {exc}"]

        if not errors:
            assert isinstance(result, dict)
            write_result(conn, item_id, result, fetch_status, item_input, item_output)
            report.items_triaged += 1
            if result["flagged"]:
                report.items_flagged += 1
            if result.get("auto_discard"):
                report.items_discarded += 1
            logger.info(
                "item=%d source=%s level=%s discard=%s flagged=%s confidence=%s attempt=%d",
                item_id,
                item["source"],
                result.get("level"),
                result.get("auto_discard"),
                result["flagged"],
                result["confidence"],
                attempt,
            )
            return

        if attempt == 1:
            logger.warning("item=%d validation failed, retrying once: %s", item_id, errors)
            prompt = retry_prompt(prompt, errors)

    write_invalid(conn, item_id, errors, raw, fetch_status, item_input, item_output)
    report.items_invalid += 1
    report.items_flagged += 1
    logger.error("item=%d invalid model output after retry: %s", item_id, errors)


def append_run_log(report: RunReport) -> None:
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report.to_json()) + "\n")


def print_report(report: RunReport) -> None:
    print("\n--- Triage run report ---")
    print(f"run_at          {report.run_at}")
    print(f"run_type        {report.run_type}")
    print(f"model           {report.model}")
    print(f"items eligible  {report.items_eligible}")
    print(f"items triaged   {report.items_triaged}")
    print(f"items flagged   {report.items_flagged}")
    print(f"items discarded {report.items_discarded}")
    print(f"items invalid   {report.items_invalid}")
    print(f"api errors      {report.items_api_error}")
    print(f"fetch failures  {report.fetch_failures}")
    print(f"input tokens    {report.input_tokens}")
    print(f"output tokens   {report.output_tokens}")
    print(f"cost USD        {report.cost_usd:.4f}")
    if report.items_api_error:
        print("\nItems left untriaged because of API errors. Re-run to retry them:")
        for line in report.api_errors:
            print(f"  {line}")


def run(limit: int | None = None, dry_run: bool = False, run_type: str = "full") -> int:
    load_dotenv()

    template = load_prompt_template()
    taxonomy_text = TAXONOMY_PATH.read_text(encoding="utf-8")
    scoring_text = SCORING_PATH.read_text(encoding="utf-8")
    taxonomy = load_taxonomy(taxonomy_text)

    conn = db.connect()
    conn.row_factory = sqlite3.Row
    migrate.migrate(conn)

    items = list(conn.execute(ELIGIBLE_SQL))
    report = RunReport(run_at=now_iso(), run_type=run_type, items_eligible=len(items))
    if limit is not None:
        items = items[:limit]
        logger.info("limit=%d, processing %d of %d eligible items", limit, len(items), report.items_eligible)

    if not items:
        logger.info("no eligible items")

    client = None
    if not dry_run:
        client = anthropic.Anthropic()

    for item in items:
        triage_item(
            client, conn, item, template, taxonomy, taxonomy_text, scoring_text, report, dry_run
        )

    conn.close()

    if dry_run:
        print(f"\nDry run: {len(items)} items prepared, no API calls, nothing written.")
        return 0

    print_report(report)
    append_run_log(report)
    return 1 if (report.items_api_error or report.items_invalid) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage untriaged items via the Claude API.")
    parser.add_argument("--limit", type=int, help="process at most N eligible items")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch pages and build prompts, but make no API calls and write nothing",
    )
    parser.add_argument(
        "--run-type",
        choices=RUN_TYPES,
        default="full",
        help="recorded in the run log so partial runs are not summed with full ones",
    )
    args = parser.parse_args()
    return run(limit=args.limit, dry_run=args.dry_run, run_type=args.run_type)


if __name__ == "__main__":
    sys.exit(main())
