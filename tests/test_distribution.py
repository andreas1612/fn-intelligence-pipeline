"""Distribution: the human gate and the idempotency guard.

Two promises are made to the client and both are enforced here:

  1. Nothing reaches a client that a person has not reviewed (D-018).
  2. Nothing is ever sent twice (delivered_at, D-024).

A regression in either is invisible in normal operation and only shows up as an
unreviewed item in a client's inbox, or the same digest sent twice.
"""

from datetime import date

import pytest

from src.distribute import channels, digest
from tests.conftest import add_client, add_item

TODAY = date(2026, 7, 14)


@pytest.fixture
def client_id(conn):
    return add_client(conn, jurisdictions=["EU"], themes=["DORA"])


def add_match(conn, item_id, client_id, score=4.0, delivered_at=None):
    conn.execute(
        "INSERT INTO matches (item_id, client_id, score, matched_on, created_at, delivered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, client_id, score, "jurisdiction: EU; theme: DORA",
         "2026-07-13T00:00:00+00:00", delivered_at),
    )
    conn.commit()


# --- The human gate -------------------------------------------------------


@pytest.mark.parametrize("status", ["Reviewed", "Published"])
def test_a_reviewed_item_is_sendable(conn, client_id, status):
    item_id = add_item(conn, review_status=status)
    add_match(conn, item_id, client_id)

    assert len(digest.undelivered(conn, client_id)) == 1


@pytest.mark.parametrize("status", ["New", "Discarded", None])
def test_an_unreviewed_or_discarded_item_never_appears_in_a_digest(conn, client_id, status):
    # The match row exists, which is the dangerous case: matching wrote it while
    # the item was Reviewed, and a reviewer then moved it back on the board. The
    # gate is re-checked at send time precisely for this.
    item_id = add_item(conn, review_status=status)
    add_match(conn, item_id, client_id)

    assert digest.undelivered(conn, client_id) == []


def test_an_auto_discarded_item_never_appears_even_if_marked_reviewed(conn, client_id):
    item_id = add_item(conn, auto_discard="AD-2", level=None, review_status="Reviewed")
    add_match(conn, item_id, client_id)

    assert digest.undelivered(conn, client_id) == []


# --- Idempotency ----------------------------------------------------------


def test_a_delivered_match_is_not_resent(conn, client_id):
    item_id = add_item(conn, review_status="Reviewed")
    add_match(conn, item_id, client_id, delivered_at="2026-07-13T09:00:00+00:00")

    assert digest.undelivered(conn, client_id) == []


def test_sending_marks_delivered_and_a_second_run_sends_nothing(conn, client_id, tmp_path):
    item_id = add_item(conn, review_status="Reviewed")
    add_match(conn, item_id, client_id)

    client = conn.execute("SELECT id, name FROM clients WHERE id = ?", (client_id,)).fetchone()
    channel = channels.FileChannel(tmp_path)

    first = digest.distribute_client(conn, client, channel, TODAY, send=True)
    assert first["sent"] is True
    assert first["items"] == 1

    second = digest.distribute_client(conn, client, channel, TODAY, send=True)
    assert second["items"] == 0
    assert second["sent"] is False


def test_a_failed_send_marks_nothing_and_is_retried(conn, client_id):
    # The guarantee that makes retries safe: delivered_at is written only after
    # the channel reports success, so a failure leaves the match in the queue.
    item_id = add_item(conn, review_status="Reviewed")
    add_match(conn, item_id, client_id)

    class BrokenChannel(channels.Channel):
        name = "broken"

        def deliver(self, client_name, markdown, on_date):
            raise channels.DeliveryError("disk full")

    client = conn.execute("SELECT id, name FROM clients WHERE id = ?", (client_id,)).fetchone()
    result = digest.distribute_client(conn, client, BrokenChannel(), TODAY, send=True)

    assert result["sent"] is False
    assert result["error"] == "disk full"
    # Still queued, so the next run picks it up again.
    assert len(digest.undelivered(conn, client_id)) == 1


def test_a_preview_marks_nothing(conn, client_id, capsys):
    item_id = add_item(conn, review_status="Reviewed")
    add_match(conn, item_id, client_id)

    client = conn.execute("SELECT id, name FROM clients WHERE id = ?", (client_id,)).fetchone()
    digest.distribute_client(conn, client, None, TODAY, send=False)

    assert len(digest.undelivered(conn, client_id)) == 1


# --- Rendering ------------------------------------------------------------


def test_the_digest_reuses_the_triage_summary_and_the_match_reason(conn, client_id):
    # No model call in distribution: the summary in the digest is the one triage
    # already wrote and a human already saw.
    item_id = add_item(
        conn, review_status="Reviewed", ai_summary="ESMA opened a consultation."
    )
    add_match(conn, item_id, client_id)

    markdown = digest.render_digest(
        "Test Client", digest.undelivered(conn, client_id), TODAY
    )

    assert "ESMA opened a consultation." in markdown
    assert "Matched on jurisdiction: EU; theme: DORA" in markdown
    assert "https://www.esma.europa.eu/example" in markdown


def test_items_are_grouped_by_level_most_urgent_first(conn, client_id):
    add_match(conn, add_item(conn, title="Low item", url="https://e.eu/1",
                             level="Low", review_status="Reviewed"), client_id, score=1.0)
    add_match(conn, add_item(conn, title="Urgent item", url="https://e.eu/2",
                             level="Urgent", review_status="Reviewed"), client_id, score=2.0)

    markdown = digest.render_digest(
        "Test Client", digest.undelivered(conn, client_id), TODAY
    )

    assert markdown.index("## Urgent") < markdown.index("## Low")


def test_empty_levels_get_no_heading(conn, client_id):
    add_match(conn, add_item(conn, review_status="Reviewed", level="High"), client_id)

    markdown = digest.render_digest(
        "Test Client", digest.undelivered(conn, client_id), TODAY
    )

    assert "## High" in markdown
    assert "## Urgent" not in markdown


# --- Channels -------------------------------------------------------------


def test_the_file_channel_writes_where_it_says_it_did(tmp_path):
    channel = channels.FileChannel(tmp_path)
    destination = channel.deliver("Cyprus EMI (example)", "# digest", TODAY)

    written = tmp_path / "cyprus-emi-example" / "2026-07-14.md"
    assert written.read_text(encoding="utf-8") == "# digest"
    assert str(written) == destination


def test_an_unknown_channel_is_fatal_not_a_silent_fallback():
    # Falling back to console would look like a successful send and mark matches
    # delivered that no client ever received.
    with pytest.raises(SystemExit):
        channels.build_channel("carrier-pigeon", config={})


def test_the_configured_channel_is_used_when_none_is_forced():
    assert channels.build_channel(None, config={"channel": "console"}).name == "console"
    assert channels.build_channel(None, config={"channel": "file"}).name == "file"


def test_an_explicit_channel_overrides_configuration():
    assert channels.build_channel("console", config={"channel": "file"}).name == "console"
