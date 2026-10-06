"""Single analytics API used by routes, predictor and import utilities."""
from collections import Counter
from itertools import combinations
from ..database.connection import connection
from ..config import GAME_CONFIG


def fetch_game_draws(game_type: str, limit: int | None = None) -> list[dict]:
    if game_type not in GAME_CONFIG:
        raise ValueError(f"Unsupported game_type: {game_type}")
    query = "SELECT * FROM draws WHERE game_type=? ORDER BY draw_datetime, CAST(draw_number AS INTEGER)"
    args = [game_type]
    if limit:
        query = f"SELECT * FROM ({query}) q ORDER BY draw_datetime DESC LIMIT ?"
        args.append(limit)
    with connection() as conn:
        rows = conn.execute(query, args).fetchall()
    return [{"numbers": [int(r[f"n{i}"]) for i in range(1, 7)
                         if r[f"n{i}"] is not None],
             "special_number": r["special_number"], "draw_datetime": r["draw_datetime"]}
            for r in rows]


def _numbers(game_type: str, limit: int | None = None):
    return [n for d in fetch_game_draws(game_type, limit) for n in d["numbers"]]


def get_frequency_table(game_type: str, lookback: int | None = None):
    c = Counter(_numbers(game_type, lookback))
    return [{"number": n, "count": c[n]} for n in range(1, GAME_CONFIG[game_type]["max_number"] + 1)]


def get_hot_numbers(game_type: str, lookback: int = 20, top_n: int = 10):
    return [x["number"] for x in sorted(get_frequency_table(game_type, lookback),
                                         key=lambda x: (-x["count"], x["number"]))[:top_n]]


def get_cold_numbers(game_type: str, lookback: int = 100, top_n: int = 10):
    return [x["number"] for x in sorted(get_frequency_table(game_type, lookback),
                                         key=lambda x: (x["count"], x["number"]))[:top_n]]


def get_overdue_numbers(game_type: str):
    draws = fetch_game_draws(game_type)
    out = []
    for n in range(1, GAME_CONFIG[game_type]["max_number"] + 1):
        gap = next((i for i, d in enumerate(reversed(draws)) if n in d["numbers"]), len(draws))
        out.append({"number": n, "gap": gap, "overdue_ratio": gap / max(1, len(draws))})
    return sorted(out, key=lambda x: (-x["gap"], x["number"]))


def get_expected_gap(game_type: str):
    return GAME_CONFIG[game_type]["max_number"] / GAME_CONFIG[game_type]["numbers_per_draw"]


def get_monthly_frequency(game_type: str):
    result = {}
    for d in fetch_game_draws(game_type):
        result.setdefault(str(d["draw_datetime"])[:7], Counter()).update(d["numbers"])
    return {month: dict(counter) for month, counter in result.items()}


def get_yearly_frequency(game_type: str):
    result = {}
    for draw in fetch_game_draws(game_type):
        result.setdefault(str(draw["draw_datetime"])[:4], Counter()).update(
            draw["numbers"]
        )
    return {year: dict(counter) for year, counter in result.items()}


def get_top_pairs(game_type, lookback=None, top_n=10):
    c = Counter(pair for d in fetch_game_draws(game_type, lookback)
                for pair in combinations(sorted(d["numbers"]), 2))
    return [{"pair": list(k), "count": v} for k, v in c.most_common(top_n)]


def get_top_triplets(game_type, lookback=None, top_n=10):
    c = Counter(tri for d in fetch_game_draws(game_type, lookback)
                for tri in combinations(sorted(d["numbers"]), 3))
    return [{"triplet": list(k), "count": v} for k, v in c.most_common(top_n)]


def get_gaps(game_type): return get_overdue_numbers(game_type)
def get_trends(game_type, lookback=20):
    recent = Counter(_numbers(game_type, lookback))
    previous = Counter(_numbers(game_type, lookback * 2))
    return {
        number: float(recent[number] - max(0, previous[number] - recent[number]))
        for number in range(1, GAME_CONFIG[game_type]["max_number"] + 1)
    }
def get_momentum(game_type, lookback=10):
    recent = Counter(_numbers(game_type, lookback))
    previous = Counter(_numbers(game_type, lookback * 2))
    return {
        number: recent[number] - max(0, previous[number] - recent[number])
        for number in range(1, GAME_CONFIG[game_type]["max_number"] + 1)
    }

def get_confidence(game_type): return {"baseline": 0.0, "validated": False}
