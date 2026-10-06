"""Pair and triplet analysis for Vietlott results."""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = (PROJECT_ROOT / "data" / "vietlot.sqlite").resolve()

GAME_CONFIG: dict[str, dict[str, int]] = {
    "5_35": {"max_number": 35, "numbers_per_draw": 5},
    "6_45": {"max_number": 45, "numbers_per_draw": 6},
    "6_55": {"max_number": 55, "numbers_per_draw": 6},
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def detect_draw_table(conn: sqlite3.Connection) -> str | None:
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('draws', 'lottery_draws')"
        )
    ]
    if "draws" in tables:
        return "draws"
    if "lottery_draws" in tables:
        return "lottery_draws"
    return None


def get_number_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    """Return only n-columns present in the SQLite table."""
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info('{table_name}')")
    }
    return [f"n{i}" for i in range(1, 7) if f"n{i}" in columns]


def fetch_recent_draws(game_type: str, lookback: int | None = None) -> list[list[int]]:
    """Fetch numbers by draw, optionally capped by lookback count."""
    if game_type not in GAME_CONFIG:
        raise ValueError(f"Unsupported game_type: {game_type}")

    with get_connection() as conn:
        table_name = detect_draw_table(conn)
        if table_name is None:
            return []
        number_columns = get_number_columns(conn, table_name)
        if not number_columns:
            return []
        number_sql = ", ".join(number_columns)
        query = f"""
            SELECT {number_sql}
            FROM {table_name}
            WHERE game_type = ?
            ORDER BY draw_datetime DESC, CAST(draw_number AS INTEGER) DESC
        """
        params: tuple[Any, ...] = (game_type,)
        if lookback is not None:
            query += " LIMIT ?"
            params = (game_type, lookback)
        rows = conn.execute(query, params).fetchall()

    result: list[list[int]] = []
    for row in rows:
        available_columns = set(row.keys())
        numbers = [
            int(row[column])
            for column in number_columns
            if column in available_columns and row[column] is not None
        ]
        result.append(sorted(numbers))
    return list(reversed(result))


def _pair_counts(draws: list[list[int]]) -> Counter[tuple[int, int]]:
    counts: Counter[tuple[int, int]] = Counter()
    for draw in draws:
        for index, first in enumerate(draw):
            for second in draw[index + 1 :]:
                pair = tuple(sorted((first, second)))
                counts[pair] += 1
    return counts


def _triplet_counts(draws: list[list[int]]) -> Counter[tuple[int, int, int]]:
    counts: Counter[tuple[int, int, int]] = Counter()
    for draw in draws:
        for i in range(len(draw)):
            for j in range(i + 1, len(draw)):
                for k in range(j + 1, len(draw)):
                    triplet = tuple(sorted((draw[i], draw[j], draw[k])))
                    counts[triplet] += 1
    return counts


def get_top_pairs(game_type: str, lookback: int | None = None, top_n: int = 10) -> list[dict[str, Any]]:
    """Return the most frequent pairs in a given lookback window."""
    draws = fetch_recent_draws(game_type, lookback)
    counts = _pair_counts(draws)
    return [
        {"pair": [first, second], "count": count}
        for (first, second), count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n]
    ]


def get_top_triplets(game_type: str, lookback: int | None = None, top_n: int = 10) -> list[dict[str, Any]]:
    """Return the most frequent triplets in a given lookback window."""
    draws = fetch_recent_draws(game_type, lookback)
    counts = _triplet_counts(draws)
    return [
        {"triplet": list(triple), "count": count}
        for triple, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n]
    ]


if __name__ == "__main__":
    for game in ("5_35", "6_45", "6_55"):
        print(f"Game {game}")
        print("Top pairs: ", get_top_pairs(game, 50, 10))
        print("Top triplets: ", get_top_triplets(game, 100, 10))
        print()
