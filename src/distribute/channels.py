"""Delivery channels: pluggable output, one per destination (D-024).

The intake side has one collector per source behind a shared interface. This is
the same shape for output: one channel per destination behind `deliver`. The
caller in digest.py never names a channel; it asks the registry for whichever
channel configuration selects, so adding a channel is a new class plus a config
line, never an edit at the call site.

A channel reports success by returning normally. It reports failure by raising
DeliveryError. The caller marks matches delivered only on success, so a failed
send leaves delivered_at null and the next run retries it.

Channels built: file, console. Email is deferred (D-024): the stack already
names SendGrid (D-003), but sending to a real address is out of scope until the
example clients in config/clients.yaml are replaced with real ones.

Configuration: config/distribution.yaml.
"""

import sys
from datetime import date
from pathlib import Path

import yaml

from src.collectors.base import logger

ROOT = Path(__file__).resolve().parent.parent.parent
DISTRIBUTION_CONFIG = ROOT / "config" / "distribution.yaml"

# Written to by the file channel. Gitignored: digests are reproducible from the
# database, so committing them would add churn without adding an audit trail.
DEFAULT_OUTPUT_DIR = ROOT / "data" / "digests"

DEFAULT_CHANNEL = "console"


class DeliveryError(Exception):
    """A channel failed to deliver. The caller must not mark anything delivered."""


def slug(name: str) -> str:
    """Filesystem-safe client name. Client names are owner-authored, not model
    output, but they reach a path here, so they are constrained rather than
    trusted: everything outside [a-z0-9] becomes a single hyphen.

        "Cyprus EMI (example)" -> "cyprus-emi-example"
    """
    kept = "".join(c.lower() if c.isalnum() else "-" for c in name)
    return "-".join(part for part in kept.split("-") if part) or "client"


class Channel:
    """One destination. Subclasses implement deliver()."""

    name = "channel"

    def deliver(self, client_name: str, markdown: str, on_date: date) -> str:
        """Send one client's digest. Return a human-readable destination.

        Raise DeliveryError on failure. Returning normally means delivered, and
        the caller will write delivered_at on the strength of it.
        """
        raise NotImplementedError


class FileChannel(Channel):
    """Write the digest to data/digests/<client>/<date>.md."""

    name = "file"

    def __init__(self, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
        self.output_dir = Path(output_dir)

    def deliver(self, client_name: str, markdown: str, on_date: date) -> str:
        path = self.output_dir / slug(client_name) / f"{on_date.isoformat()}.md"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            raise DeliveryError(f"could not write {path}: {exc}") from exc
        return str(path)


class ConsoleChannel(Channel):
    """Print the digest. Useful for review before a real channel is trusted."""

    name = "console"

    def deliver(self, client_name: str, markdown: str, on_date: date) -> str:
        print()
        print(markdown)
        return "console"


CHANNELS: dict[str, type[Channel]] = {
    FileChannel.name: FileChannel,
    ConsoleChannel.name: ConsoleChannel,
}


def load_config(path: Path = DISTRIBUTION_CONFIG) -> dict:
    if not path.exists():
        logger.warning("%s not found, defaulting to the %s channel", path.name, DEFAULT_CHANNEL)
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_channel(name: str | None = None, config: dict | None = None) -> Channel:
    """Return the configured channel. `name` overrides configuration (CLI flag).

    An unknown channel name is fatal. Silently falling back to console would look
    like a successful send and mark matches delivered that nobody received.
    """
    settings = load_config() if config is None else config
    chosen = name or settings.get("channel") or DEFAULT_CHANNEL

    if chosen not in CHANNELS:
        raise SystemExit(
            f"Unknown channel {chosen!r}. Available: {', '.join(sorted(CHANNELS))}.\n"
            f"Set 'channel' in {DISTRIBUTION_CONFIG.name} or pass --channel."
        )

    if chosen == FileChannel.name:
        configured_dir = settings.get("output_dir")
        output_dir = ROOT / configured_dir if configured_dir else DEFAULT_OUTPUT_DIR
        return FileChannel(output_dir)

    return CHANNELS[chosen]()


def force_utf8_stdout() -> None:
    """Item titles carry non-ASCII (Greek from Cyprus sources, zero-width spaces
    from EBA). Printing a digest must never crash on a legacy console."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
