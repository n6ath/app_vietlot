"""Statistics helpers for analyzing historical Vietlott draws in SQLite."""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
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
    """Open a SQLite connection for analytics work."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def detect_draw_table(conn: sqlite3.Connection) -> str | None:
    """Support both legacy and current draw-table names."""
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
    """Return number columns that actually exist in the selected table."""
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info('{table_name}')")
    }
    return [f"n{i}" for i in range(1, 7) if f"n{i}" in columns]


def fetch_game_draws(game_type: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Fetch ordered draws for one game type from SQLite."""
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
        order_sql = "DESC" if limit is not None else "ASC"
        query = f"""
            SELECT game_type, draw_number, draw_datetime,
                   {number_sql}
            FROM {table_name}
            WHERE game_type = ?
            ORDER BY draw_datetime {order_sql}, CAST(draw_number AS INTEGER) {order_sql}
        """
        if limit is not None:
            query += " LIMIT ?"
            params: tuple[Any, ...] = (game_type, limit)
        else:
            params = (game_type,)
        rows = conn.execute(query, params).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        available_columns = set(row.keys())
        numbers = [
            int(row[column])
            for column in number_columns
            if column in available_columns and row[column] is not None
        ]
        result.append(
            {
                "game_type": row["game_type"],
                "draw_number": str(row["draw_number"]),
                "draw_datetime": row["draw_datetime"],
                "numbers": numbers,
            }
        )
    return list(reversed(result)) if limit is not None else result


def _number_range(game_type: str) -> range:
    config = GAME_CONFIG[game_type]
    return range(1, config["max_number"] + 1)


def _recent_counts(game_type: str, lookback: int) -> Counter[int]:
    draws = fetch_game_draws(game_type, limit=lookback)
    counter: Counter[int] = Counter()
    for draw in draws:
        for number in draw["numbers"]:
            counter[number] += 1
    return counter


def get_hot_numbers(game_type: str, lookback: int = 20, top_n: int = 10) -> list[int]:
    """Return the most frequently appearing numbers over the last N draws."""
    counts = _recent_counts(game_type, lookback)
    if not counts:
        return []
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [number for number, _ in ranked[:top_n]]


def get_cold_numbers(game_type: str, lookback: int = 100, top_n: int = 10) -> list[int]:
    """Return the least frequent numbers in the most recent lookback window."""
    counts = _recent_counts(game_type, lookback)
    if not counts:
        return []
    all_numbers = list(_number_range(game_type))
    for number in all_numbers:
        counts.setdefault(number, 0)
    ranked = sorted(counts.items(), key=lambda item: (item[1], item[0]))
    return [number for number, _ in ranked[:top_n]]


def _last_seen_by_number(game_type: str) -> dict[int, int]:
    draws = fetch_game_draws(game_type)
    last_seen: dict[int, int] = {}
    for draw in draws:
        for number in draw["numbers"]:
            last_seen[number] = int(str(draw["draw_number"]).strip() or 0)
    return last_seen


def _draw_number_index(draws: list[dict[str, Any]]) -> int:
    if not draws:
        return 0
    numbers = [int(str(draw["draw_number"]).strip()) for draw in draws]
    return max(numbers)


def _overdue_metrics(game_type: str) -> list[dict[str, Any]]:
    draws = fetch_game_draws(game_type)
    if not draws:
        return []

    total_draws = len(draws)
    last_draw_number = _draw_number_index(draws)
    last_seen = _last_seen_by_number(game_type)
    last_seen_position: dict[int, int] = {}
    lifetime_counts = Counter()
    for position, draw in enumerate(draws):
        for number in draw["numbers"]:
            lifetime_counts[number] += 1
            last_seen_position[number] = position

    metrics: list[dict[str, Any]] = []
    for number in _number_range(game_type):
        total_appearances = lifetime_counts.get(number, 0)
        if total_appearances == 0:
            average_gap = float("inf")
            current_gap = last_draw_number + 1
            overdue_ratio = 0.0
            last_seen_draw = None
        else:
            average_gap = (total_draws / total_appearances) if total_appearances else 0.0
            last_seen_draw = last_seen.get(number)
            if number not in last_seen_position:
                current_gap = total_draws
            else:
                current_gap = total_draws - 1 - last_seen_position[number]
            overdue_ratio = (current_gap / average_gap) if average_gap else 0.0
        metrics.append(
            {
                "number": number,
                "count": total_appearances,
                "last_seen_draw": last_seen_draw,
                "current_gap": current_gap,
                "average_gap": average_gap,
                "overdue_ratio": overdue_ratio,
            }
        )
    metrics.sort(key=lambda item: (-item["overdue_ratio"], -item["count"], item["number"]))
    return metrics


def get_overdue_numbers(game_type: str) -> list[dict[str, Any]]:
    """Return numbers sorted by overdue ratio, including gap metrics."""
    metrics = _overdue_metrics(game_type)
    return [
        {
            "number": item["number"],
            "count": item["count"],
            "last_seen_draw": item["last_seen_draw"],
            "current_gap": item["current_gap"],
            "average_gap": round(item["average_gap"], 2) if item["average_gap"] != float("inf") else None,
            "overdue_ratio": round(item["overdue_ratio"], 4),
        }
        for item in metrics
    ]


def get_frequency_table(game_type: str) -> list[dict[str, Any]]:
    """Return lifetime frequency counts for each number."""
    draws = fetch_game_draws(game_type)
    counts: Counter[int] = Counter()
    for draw in draws:
        for number in draw["numbers"]:
            counts[number] += 1
    return [
        {"number": number, "count": count}
        for number, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def get_monthly_frequency(game_type: str) -> list[dict[str, Any]]:
    """Aggregate draws by year-month and number count."""
    draws = fetch_game_draws(game_type)
    monthly: defaultdict[str, Counter[int]] = defaultdict(Counter)
    for draw in draws:
        draw_time = str(draw["draw_datetime"])[:7]
        for number in draw["numbers"]:
            monthly[draw_time][number] += 1

    result: list[dict[str, Any]] = []
    for month in sorted(monthly):
        for number, count in sorted(monthly[month].items(), key=lambda item: (item[0])):
            result.append({"month": month, "number": number, "count": count})
    return result


def get_expected_gap(game_type: str) -> list[dict[str, Any]]:
    """Return overdue-style ranking using average gap and current gap."""
    metrics = _overdue_metrics(game_type)
    return [
        {
            "number": item["number"],
            "count": item["count"],
            "average_gap": round(item["average_gap"], 2) if item["average_gap"] != float("inf") else None,
            "current_gap": item["current_gap"],
            "overdue_ratio": round(item["overdue_ratio"], 4),
        }
        for item in metrics
    ]


if __name__ == "__main__":
    for game in ("5_35", "6_45", "6_55"):
        print(f"Game {game}")
        print("Hot:", get_hot_numbers(game, 20, 10))
        print("Cold:", get_cold_numbers(game, 100, 10))
        print("Overdue top 5:", get_overdue_numbers(game)[:5])
        print("Expected gap top 5:", get_expected_gap(game)[:5])
        print()
