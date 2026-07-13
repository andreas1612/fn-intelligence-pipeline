"""Client register and profile seeding for intelligence matching.

Clients and their interest profiles live in config/clients.yaml (version
controlled, per the project convention that configuration lives in files). This
module validates every profile tag against the locked taxonomy
(docs/taxonomy-v1.0.md) and the scoring levels, then seeds them into SQLite,
which stays the system of record (D-008).

Tables owned here (additive, created if absent, never dropped):
    clients(id, name UNIQUE, active, min_level)
    client_sectors(client_id, sector_tag)
    client_jurisdictions(client_id, jurisdiction_tag)
    client_themes(client_id, theme_tag)

Seeding is idempotent: a client is matched by name, its profile rows are
replaced, and existing match rows are never touched here.

Run with:
    python -m src.clients seed
    python -m src.clients list
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import yaml

from src import db
from src.collectors.base import logger
from src.triage import LEVELS, TAXONOMY_PATH, load_taxonomy

ROOT = Path(__file__).resolve().parent.parent
CLIENTS_CONFIG = ROOT / "config" / "clients.yaml"

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    active     INTEGER NOT NULL DEFAULT 1,
    min_level  TEXT NOT NULL DEFAULT 'Standard'
);
CREATE TABLE IF NOT EXISTS client_sectors (
    client_id  INTEGER NOT NULL,
    sector_tag TEXT NOT NULL,
    UNIQUE(client_id, sector_tag)
);
CREATE TABLE IF NOT EXISTS client_jurisdictions (
    client_id        INTEGER NOT NULL,
    jurisdiction_tag TEXT NOT NULL,
    UNIQUE(client_id, jurisdiction_tag)
);
CREATE TABLE IF NOT EXISTS client_themes (
    client_id  INTEGER NOT NULL,
    theme_tag  TEXT NOT NULL,
    UNIQUE(client_id, theme_tag)
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def load_clients_config(path: Path = CLIENTS_CONFIG) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} not found. Create it (see config/clients.yaml example).")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    clients = data.get("clients", [])
    if not isinstance(clients, list):
        raise SystemExit(f"{path}: top-level 'clients' must be a list.")
    return clients


def validate(clients: list[dict], taxonomy) -> list[str]:
    """Return a list of validation errors. Empty list means the config is usable."""
    errors: list[str] = []
    seen_names: set[str] = set()

    for index, client in enumerate(clients):
        name = client.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"client {index}: missing or empty 'name'")
            continue
        if name in seen_names:
            errors.append(f"client {name!r}: duplicate name")
        seen_names.add(name)

        level = client.get("min_level", "Standard")
        if level not in LEVELS:
            errors.append(f"client {name!r}: min_level {level!r} not one of {LEVELS}")

        for tag in client.get("sectors", []) or []:
            if tag not in taxonomy.sectors:
                errors.append(f"client {name!r}: sector {tag!r} not in taxonomy")
        for tag in client.get("jurisdictions", []) or []:
            if tag not in taxonomy.jurisdictions:
                errors.append(f"client {name!r}: jurisdiction {tag!r} not in taxonomy")
        for tag in client.get("themes", []) or []:
            if tag not in taxonomy.themes:
                errors.append(f"client {name!r}: theme {tag!r} not in taxonomy")

        if not (client.get("sectors") or client.get("jurisdictions") or client.get("themes")):
            errors.append(
                f"client {name!r}: empty profile (needs at least one sector, jurisdiction, or theme)"
            )

    return errors


def _replace_profile(conn, client_id, table, column, values) -> None:
    conn.execute(f"DELETE FROM {table} WHERE client_id = ?", (client_id,))
    for value in dict.fromkeys(values):  # de-duplicate, preserve order
        conn.execute(
            f"INSERT OR IGNORE INTO {table} (client_id, {column}) VALUES (?, ?)",
            (client_id, value),
        )


def seed(conn: sqlite3.Connection) -> int:
    """Seed clients from config into SQLite. Idempotent (upsert by name)."""
    ensure_schema(conn)
    taxonomy = load_taxonomy(TAXONOMY_PATH.read_text(encoding="utf-8"))
    clients = load_clients_config()

    errors = validate(clients, taxonomy)
    if errors:
        for error in errors:
            logger.error("clients.yaml invalid: %s", error)
        raise SystemExit(f"{len(errors)} validation error(s); nothing seeded.")

    for client in clients:
        name = client["name"]
        active = 1 if client.get("active", True) else 0
        min_level = client.get("min_level", "Standard")

        conn.execute(
            "INSERT INTO clients (name, active, min_level) VALUES (?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET active = excluded.active, "
            "min_level = excluded.min_level",
            (name, active, min_level),
        )
        client_id = conn.execute(
            "SELECT id FROM clients WHERE name = ?", (name,)
        ).fetchone()[0]

        _replace_profile(conn, client_id, "client_sectors", "sector_tag", client.get("sectors", []) or [])
        _replace_profile(conn, client_id, "client_jurisdictions", "jurisdiction_tag", client.get("jurisdictions", []) or [])
        _replace_profile(conn, client_id, "client_themes", "theme_tag", client.get("themes", []) or [])

    conn.commit()
    logger.info("seeded %d client(s) from %s", len(clients), CLIENTS_CONFIG.name)
    return len(clients)


def print_clients(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, name, active, min_level FROM clients ORDER BY name").fetchall()
    if not rows:
        print("No clients seeded. Run: python -m src.clients seed")
        return
    for row in rows:
        state = "active" if row["active"] else "inactive"
        sectors = [r[0] for r in conn.execute("SELECT sector_tag FROM client_sectors WHERE client_id = ?", (row["id"],))]
        juris = [r[0] for r in conn.execute("SELECT jurisdiction_tag FROM client_jurisdictions WHERE client_id = ?", (row["id"],))]
        themes = [r[0] for r in conn.execute("SELECT theme_tag FROM client_themes WHERE client_id = ?", (row["id"],))]
        print(f"\n{row['name']}  [{state}, min_level={row['min_level']}]")
        print(f"  sectors:       {', '.join(sectors) or '(any)'}")
        print(f"  jurisdictions: {', '.join(juris) or '(any)'}")
        print(f"  themes:        {', '.join(themes) or '(any)'}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="Seed and inspect the client register.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="validate config/clients.yaml and seed clients into SQLite")
    sub.add_parser("list", help="show seeded clients and their profiles")
    args = parser.parse_args()

    conn = db.connect()
    if args.command == "seed":
        count = seed(conn)
        print(f"Seeded {count} client(s).")
    else:
        print_clients(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
