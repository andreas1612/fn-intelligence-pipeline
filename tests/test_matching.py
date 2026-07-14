"""The matching rule: tag overlap, level gate, scoring.

A silent regression here misroutes intelligence to the wrong client, or drops it
silently, and nothing downstream would notice.
"""

import pytest

from src import matching
from tests.conftest import add_client, add_item


def profile(sectors=(), jurisdictions=(), themes=(), min_level="Standard"):
    return {
        "id": 1,
        "name": "Test Client",
        "min_level": min_level,
        "sectors": set(sectors),
        "jurisdictions": set(jurisdictions),
        "themes": set(themes),
    }


# --- Scoring --------------------------------------------------------------


def test_no_overlap_is_not_a_match():
    # The whole product rests on this: a client is never sent an item that has
    # nothing to do with them.
    result = matching.score_match(
        {"Insurance"}, {"International"}, {"AI security"},
        profile(sectors=["Investment firms"], jurisdictions=["EU"], themes=["DORA"]),
    )
    assert result is None


def test_jurisdiction_outweighs_sector_which_outweighs_theme():
    j = matching.score_match(set(), {"EU"}, set(), profile(jurisdictions=["EU"]))
    s = matching.score_match({"Insurance"}, set(), set(), profile(sectors=["Insurance"]))
    t = matching.score_match(set(), set(), {"DORA"}, profile(themes=["DORA"]))
    assert j[0] > s[0] > t[0]
    assert (j[0], s[0], t[0]) == (3.0, 2.0, 1.0)


def test_score_sums_every_overlapping_tag():
    score, _ = matching.score_match(
        {"Investment firms"}, {"EU"}, {"DORA", "Operational resilience"},
        profile(
            sectors=["Investment firms"],
            jurisdictions=["EU"],
            themes=["DORA", "Operational resilience"],
        ),
    )
    # 3 (jurisdiction) + 2 (sector) + 1 + 1 (two themes)
    assert score == 7.0


def test_matched_on_names_every_reason():
    # matched_on is what the client reads in the digest to understand why they
    # were sent something. It must be complete and stable, not a summary.
    _, reason = matching.score_match(
        {"Investment firms"}, {"EU"}, {"DORA"},
        profile(sectors=["Investment firms"], jurisdictions=["EU"], themes=["DORA"]),
    )
    assert reason == "jurisdiction: EU; sector: Investment firms; theme: DORA"


def test_matched_on_omits_dimensions_that_did_not_overlap():
    _, reason = matching.score_match(
        {"Insurance"}, {"EU"}, set(), profile(jurisdictions=["EU"], sectors=["Banks"]),
    )
    assert reason == "jurisdiction: EU"


# --- Level gate -----------------------------------------------------------


@pytest.mark.parametrize(
    "item_level, min_level, expected",
    [
        ("Urgent", "Low", True),       # most urgent clears the loosest gate
        ("Urgent", "Urgent", True),    # equal clears: the gate is "at least as urgent"
        ("High", "Urgent", False),     # below the gate
        ("Standard", "High", False),
        ("Low", "Standard", False),
        ("Low", "Low", True),
        (None, "Low", False),          # an untriaged item has no level and never matches
    ],
)
def test_level_gate(item_level, min_level, expected):
    assert matching._level_ok(item_level, min_level) is expected


# --- End to end, against the database -------------------------------------


def test_reviewed_item_matches_a_client_who_shares_a_tag(conn):
    add_client(conn, jurisdictions=["EU"], themes=["DORA"])
    add_item(conn, review_status="Reviewed")

    results = matching.compute_matches(conn)

    assert len(results) == 1
    assert results[0]["client_name"] == "Test Client"
    assert "theme: DORA" in results[0]["matched_on"]


def test_level_gate_excludes_an_item_below_the_clients_floor(conn):
    add_client(conn, min_level="Urgent", jurisdictions=["EU"], themes=["DORA"])
    add_item(conn, level="High", review_status="Reviewed")

    assert matching.compute_matches(conn) == []


def test_matching_is_idempotent_and_never_clears_delivered_at(conn):
    # Re-running the pipeline must not resurrect an already-sent match. If a
    # second run cleared delivered_at, every client would be re-sent everything.
    client_id = add_client(conn, jurisdictions=["EU"], themes=["DORA"])
    item_id = add_item(conn, review_status="Reviewed")

    conn.execute(
        "INSERT INTO matches (item_id, client_id, score, matched_on, created_at, delivered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, client_id, 4.0, "theme: DORA", "2026-07-10T00:00:00+00:00",
         "2026-07-11T00:00:00+00:00"),
    )
    conn.commit()

    for result in matching.compute_matches(conn):
        conn.execute(
            "INSERT INTO matches (item_id, client_id, score, matched_on, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(item_id, client_id) DO UPDATE SET "
            "score = excluded.score, matched_on = excluded.matched_on",
            (result["item_id"], result["client_id"], result["score"],
             result["matched_on"], "2026-07-12T00:00:00+00:00"),
        )
    conn.commit()

    delivered_at = conn.execute(
        "SELECT delivered_at FROM matches WHERE item_id = ? AND client_id = ?",
        (item_id, client_id),
    ).fetchone()[0]
    assert delivered_at == "2026-07-11T00:00:00+00:00"


def test_an_inactive_client_is_never_matched(conn):
    add_client(conn, active=0, jurisdictions=["EU"], themes=["DORA"])
    add_item(conn, review_status="Reviewed")

    assert matching.compute_matches(conn) == []
