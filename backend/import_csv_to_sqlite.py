"""Validate and import Vietlott CSV data into SQLite.

The crawler CSV may contain a ``bonus_number`` column. The current SQLite
contract intentionally does not store it, so that optional CSV field is
validated for shape but ignored during insertion. A separate
``--special-csv`` mode safely updates missing Power 5/35 special numbers.
"""

from __future__ import annotations

import csv
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "vietlot.sqlite"
DEFAULT_CSV_PATH = DATA_DIR / "535_special_numbers.csv"

SUPPORTED_GAMES = {
    "5_35": {"required_numbers": 5, "min_number": 1, "max_number": 35},
    "6_45": {"required_numbers": 6, "min_number": 1, "max_number": 45},
    "6_55": {"required_numbers": 6, "min_number": 1, "max_number": 55},
}
CSV_REQUIRED_COLUMNS = {
    "game_type",
    "draw_number",
    "draw_datetime",
    "n1",
    "n2",
    "n3",
    "n4",
    "n5",
    "n6",
    "created_at",
    "source",
}
CSV_OPTIONAL_COLUMNS = {"bonus_number", "id"}
DATABASE_COLUMNS = (
    "game_type",
    "draw_number",
    "draw_datetime",
    "n1",
    "n2",
    "n3",
    "n4",
    "n5",
    "n6",
    "created_at",
    "source",
)
LOGGER = logging.getLogger("vietlot-import")
SPECIAL_CSV_COLUMNS = {
    "game_type",
    "draw_number",
    "draw_datetime",
    "special_number",
}


def configure_logging() -> None:
    """Configure concise, useful command-line logging."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def validate_game_type(value: Any) -> str:
    game_type = str(value or "").strip()
    if game_type not in SUPPORTED_GAMES:
        raise ValueError(f"unsupported game_type {value!r}")
    return game_type


def validate_draw_number(value: Any) -> str:
    """Validate and preserve the source draw number's leading zeroes."""
    text = str(value or "").strip()
    if not text or not text.isdigit() or int(text) <= 0:
        raise ValueError(f"draw_number must be a positive integer string, got {value!r}")
    return text.zfill(5)


def parse_datetime(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is empty")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except ValueError as exc:
        raise ValueError(f"invalid {field_name} {value!r}") from exc


def parse_number(value: Any, field_name: str) -> int:
    text = str(value or "").strip()
    if not text or not text.isdigit():
        raise ValueError(f"{field_name} must be an integer, got {value!r}")
    return int(text)


def validate_numbers(game_type: str, values: list[int]) -> list[int]:
    config = SUPPORTED_GAMES[game_type]
    if len(values) != config["required_numbers"]:
        raise ValueError(
            f"{game_type} requires {config['required_numbers']} main numbers; got {len(values)}"
        )
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate main numbers: {values}")
    if any(value < config["min_number"] or value > config["max_number"] for value in values):
        raise ValueError(
            f"main numbers must be in {config['min_number']}..{config['max_number']}: {values}"
        )
    return sorted(values)


def validate_bonus(game_type: str, value: Any) -> None:
    """Validate optional CSV bonus data without storing it in the current schema."""
    text = str(value or "").strip()
    if not text:
        return
    bonus = parse_number(text, "bonus_number")
    config = SUPPORTED_GAMES[game_type]
    if bonus < config["min_number"] or bonus > config["max_number"]:
        raise ValueError(f"bonus_number outside valid range: {bonus}")


def normalize_row(row: dict[str, str]) -> tuple[Any, ...]:
    """Validate one CSV row and return values matching DATABASE_COLUMNS."""
    game_type = validate_game_type(row.get("game_type"))
    draw_number = validate_draw_number(row.get("draw_number"))
    draw_datetime = parse_datetime(row.get("draw_datetime"), "draw_datetime")
    numbers = [
        parse_number(row.get(f"n{index}"), f"n{index}") for index in range(1, 6)
    ]
    n6_text = str(row.get("n6") or "").strip()
    if game_type == "5_35":
        if n6_text:
            raise ValueError("5_35 must have an empty n6")
    else:
        numbers.append(parse_number(n6_text, "n6"))
    numbers = validate_numbers(game_type, numbers)
    validate_bonus(game_type, row.get("bonus_number"))
    created_at = parse_datetime(
        row.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "created_at",
    )
    source = str(row.get("source") or "").strip()
    if not source:
        raise ValueError("source is empty")
    n6 = numbers[5] if len(numbers) == 6 else None
    return (
        game_type,
        draw_number,
        draw_datetime,
        numbers[0],
        numbers[1],
        numbers[2],
        numbers[3],
        numbers[4],
        n6,
        created_at,
        source,
    )


def ensure_database(conn: sqlite3.Connection) -> None:
    """Create the table and indexes inside the caller's transaction."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS draws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT NOT NULL,
            draw_number TEXT NOT NULL,
            draw_datetime TEXT NOT NULL,
            n1 INTEGER NOT NULL,
            n2 INTEGER NOT NULL,
            n3 INTEGER NOT NULL,
            n4 INTEGER NOT NULL,
            n5 INTEGER NOT NULL,
            n6 INTEGER,
            created_at TEXT NOT NULL,
            source TEXT,
            UNIQUE (game_type, draw_number)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_draws_game_type "
        "ON draws (game_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_draws_draw_number "
        "ON draws (draw_number)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_draws_draw_datetime "
        "ON draws (draw_datetime)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_draws_game_datetime_number "
        "ON draws (game_type, draw_datetime, draw_number)"
    )
    unique_identity = False
    for index_row in conn.execute("PRAGMA index_list(draws)"):
        index_name = index_row[1]
        is_unique = index_row[2]
        if not is_unique:
            continue
        columns = [
            column_name
            for _, _, column_name in conn.execute(
                f"PRAGMA index_info({quote_sqlite_identifier(index_name)})"
            )
        ]
        if columns == ["game_type", "draw_number"]:
            unique_identity = True
            break
    if not unique_identity:
        conn.execute(
            "CREATE UNIQUE INDEX uq_draws_game_draw "
            "ON draws (game_type, draw_number)"
        )


def migrate_special_number_column(db_path: Path = DB_PATH) -> bool:
    """Add the nullable special_number column without changing any rows."""
    with sqlite3.connect(db_path) as conn:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(draws)")
        }
        if "draws" not in {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            raise RuntimeError("draws table does not exist")
        if "special_number" in columns:
            return False
        conn.execute(
            "ALTER TABLE draws ADD COLUMN special_number INTEGER NULL"
        )
        conn.commit()
        return True


def import_special_numbers(
    csv_path: Path, db_path: Path = DB_PATH
) -> dict[str, Any]:
    """Conservatively update existing 5/35 rows from a special-number CSV."""
    summary: dict[str, Any] = {
        "crawled_records": 0,
        "valid_records": 0,
        "matched": 0,
        "updated": 0,
        "already_exists": 0,
        "not_found": [],
        "date_mismatches": [],
        "duplicates": [],
        "invalid_special_numbers": [],
        "errors": [],
    }
    seen: set[tuple[str, str]] = set()
    prepared: list[tuple[str, str, str, int]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {csv_path}")
        missing = sorted(SPECIAL_CSV_COLUMNS - set(reader.fieldnames))
        if missing:
            raise ValueError(f"Special CSV missing columns: {missing}")
        for line_number, row in enumerate(reader, start=2):
            summary["crawled_records"] += 1
            try:
                if row.get("game_type", "").strip() != "5_35":
                    raise ValueError("game_type must be 5_35")
                draw_number = validate_draw_number(row.get("draw_number"))
                draw_datetime = parse_datetime(
                    row.get("draw_datetime"), "draw_datetime"
                )
                special = parse_number(
                    row.get("special_number"), "special_number"
                )
                if not 1 <= special <= SUPPORTED_GAMES["5_35"]["max_number"]:
                    raise ValueError("special_number outside 1..35")
                key = ("5_35", draw_number)
                if key in seen:
                    summary["duplicates"].append(
                        f"line {line_number}: {draw_number}"
                    )
                    continue
                seen.add(key)
                prepared.append(("5_35", draw_number, draw_datetime, special))
                summary["valid_records"] += 1
            except (TypeError, ValueError) as exc:
                message = f"line {line_number}: {exc}"
                summary["invalid_special_numbers"].append(message)

    migrate_special_number_column(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for game_type, draw_number, draw_datetime, special in prepared:
            row = conn.execute(
                """
                SELECT draw_datetime, special_number
                FROM draws
                WHERE game_type = ? AND draw_number = ?
                """,
                (game_type, draw_number),
            ).fetchone()
            if row is None:
                summary["not_found"].append(draw_number)
                continue
            if row["draw_datetime"] != draw_datetime:
                summary["date_mismatches"].append(
                    f"{draw_number}: CSV={draw_datetime}, DB={row['draw_datetime']}"
                )
                continue
            summary["matched"] += 1
            if row["special_number"] is not None:
                summary["already_exists"] += 1
                continue
            cursor = conn.execute(
                """
                UPDATE draws
                SET special_number = ?
                WHERE game_type = ? AND draw_number = ?
                  AND special_number IS NULL
                """,
                (special, game_type, draw_number),
            )
            summary["updated"] += cursor.rowcount
        conn.commit()
    return summary


def quote_sqlite_identifier(identifier: str) -> str:
    """Quote an identifier for PRAGMA index_info without accepting SQL syntax."""
    return "'" + identifier.replace("'", "''") + "'"


def read_csv_rows(csv_path: Path) -> tuple[list[tuple[Any, ...]], int, int]:
    """Read and validate all rows before any database insert."""
    prepared: list[tuple[Any, ...]] = []
    total_rows = 0
    invalid_rows = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {csv_path}")
        missing = sorted(CSV_REQUIRED_COLUMNS - set(reader.fieldnames))
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        for line_number, row in enumerate(reader, start=2):
            total_rows += 1
            try:
                prepared.append(normalize_row(row))
            except (TypeError, ValueError) as exc:
                invalid_rows += 1
                LOGGER.warning("[INVALID] CSV line %d: %s", line_number, exc)
    return prepared, total_rows, invalid_rows


def import_csv_to_db(csv_path: Path, db_path: Path) -> dict[str, Any]:
    """Import a CSV atomically, ignoring duplicate identities."""
    rows, total_rows, invalid_rows = read_csv_rows(csv_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    inserted = 0
    skipped_duplicates = 0
    duplicate_keys: set[tuple[str, str]] = set()

    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("BEGIN")
            ensure_database(conn)
            existing_keys = {
                (game_type, draw_number)
                for game_type, draw_number in conn.execute(
                    "SELECT game_type, draw_number FROM draws"
                )
            }
            unique_rows: list[tuple[Any, ...]] = []
            for row in rows:
                key = (row[0], row[1])
                if key in existing_keys or key in duplicate_keys:
                    skipped_duplicates += 1
                    duplicate_keys.add(key)
                    continue
                duplicate_keys.add(key)
                unique_rows.append(row)

            conn.executemany(
                """
                INSERT INTO draws (
                    game_type, draw_number, draw_datetime,
                    n1, n2, n3, n4, n5, n6, created_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                unique_rows,
            )
            inserted = len(unique_rows)
            conn.commit()
    except sqlite3.Error:
        LOGGER.exception("[ERROR] Database transaction rolled back")
        raise

    with sqlite3.connect(db_path) as conn:
        game_counts = dict(
            conn.execute(
                "SELECT game_type, COUNT(*) FROM draws "
                "GROUP BY game_type ORDER BY game_type"
            ).fetchall()
        )
        earliest, latest = conn.execute(
            "SELECT MIN(draw_datetime), MAX(draw_datetime) FROM draws"
        ).fetchone()
        total_db_rows = conn.execute(        "SELECT COUNT(*) FROM draws").fetchone()[0]

    return {
        "total_rows": total_rows,
        "inserted": inserted,
        "updated": 0,
        "skipped_duplicates": skipped_duplicates,
        "invalid_rows": invalid_rows,
        "total_db_rows": total_db_rows,
        "game_counts": game_counts,
        "earliest": earliest,
        "latest": latest,
    }


def print_summary(summary: dict[str, Any], db_path: Path) -> None:
    LOGGER.info("Database: %s", db_path)
    LOGGER.info("CSV rows read: %d", summary["total_rows"])
    LOGGER.info("Inserted rows: %d", summary["inserted"])
    LOGGER.info("Updated rows: %d", summary["updated"])
    LOGGER.info("Skipped duplicates: %d", summary["skipped_duplicates"])
    LOGGER.info("Invalid rows: %d", summary["invalid_rows"])
    LOGGER.info("Total database rows: %d", summary["total_db_rows"])
    for game_type in ("5_35", "6_45", "6_55"):
        LOGGER.info("%s: %d records", game_type, summary["game_counts"].get(game_type, 0))
    LOGGER.info("Earliest draw: %s", summary["earliest"] or "N/A")
    LOGGER.info("Latest draw: %s", summary["latest"] or "N/A")


def print_special_summary(summary: dict[str, Any], db_path: Path) -> None:
    LOGGER.info("Database: %s", db_path)
    LOGGER.info("Crawled records: %d", summary["crawled_records"])
    LOGGER.info("Valid records: %d", summary["valid_records"])
    LOGGER.info("Successfully matched: %d", summary["matched"])
    LOGGER.info("Special numbers updated: %d", summary["updated"])
    LOGGER.info("Already existing: %d", summary["already_exists"])
    LOGGER.info("Not found: %d", len(summary["not_found"]))
    LOGGER.info("Date mismatches: %d", len(summary["date_mismatches"]))
    LOGGER.info("Duplicate crawler records: %d", len(summary["duplicates"]))
    LOGGER.info("Invalid special numbers: %d", len(summary["invalid_special_numbers"]))
    LOGGER.info("Errors: %d", len(summary["errors"]))
    for label in (
        "not_found",
        "date_mismatches",
        "duplicates",
        "invalid_special_numbers",
        "errors",
    ):
        values = summary[label]
        if values:
            LOGGER.info("%s:", label)
            for value in values:
                LOGGER.info("  %s", value)


def main() -> None:
    configure_logging()
    if len(sys.argv) > 1 and sys.argv[1] == "--special-csv":
        if len(sys.argv) != 3:
            raise SystemExit("Usage: python import_csv_to_sqlite.py --special-csv path")
        csv_path = Path(sys.argv[2]).expanduser().resolve()
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        summary = import_special_numbers(csv_path, DB_PATH)
        print_special_summary(summary, DB_PATH)
        return
    csv_path = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else DEFAULT_CSV_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    summary = import_csv_to_db(csv_path, DB_PATH)
    print_summary(summary, DB_PATH)


if __name__ == "__main__":
    main()
