"""Rule predictor. ML experiments are evaluated separately and never silently exposed."""
from collections import Counter
from datetime import UTC, datetime
from itertools import combinations
from .config import GAME_CONFIG
from .statistics import fetch_game_draws, get_cold_numbers, get_hot_numbers, get_overdue_numbers


def _rank(game, strategy):
    cfg = GAME_CONFIG[game]
    draws = fetch_game_draws(game)
    recent = draws[-20:]
    freq = Counter(n for d in draws for n in d["numbers"])
    recent_freq = Counter(n for d in recent for n in d["numbers"])
    pairs = Counter(p for d in draws[-50:] for p in combinations(sorted(d["numbers"]), 2))
    triples = Counter(t for d in draws[-100:] for t in combinations(sorted(d["numbers"]), 3))
    gaps = {x["number"]: x["gap"] for x in get_overdue_numbers(game)}
    pair_score = Counter(); triple_score = Counter()
    for p, count in pairs.items():
        for n in p: pair_score[n] += count
    for t, count in triples.items():
        for n in t: triple_score[n] += count
    def score(n):
        values = (gaps.get(n, 0), freq[n], recent_freq[n], pair_score[n], triple_score[n])
        weights = {"f1": (4, 2, 2, 2, 1), "f2": (7, 1, 1, 1, 1),
                   "f3": (1, 1, 5, 3, 2)}[strategy]
        return sum(a*b for a, b in zip(values, weights))
    return sorted(range(1, cfg["max_number"] + 1), key=lambda n: (-score(n), n))[:cfg["numbers_per_draw"]]


def predict_game(game_type: str):
    if game_type not in GAME_CONFIG: raise ValueError(f"Unsupported game_type: {game_type}")
    f1, f2, f3 = (_rank(game_type, x) for x in ("f1", "f2", "f3"))
    special = list(dict.fromkeys(get_hot_numbers(game_type, 20, 2) +
                                 [x["number"] for x in get_overdue_numbers(game_type)[:2]]))[:1]
    return {"game_type": game_type, "hot_numbers": get_hot_numbers(game_type, 20, 10),
            "cold_numbers": get_cold_numbers(game_type, 100, 10),
            "overdue_numbers": [x["number"] for x in get_overdue_numbers(game_type)[:10]],
            "f1_prediction": f1, "f2_prediction": f2, "f3_prediction": f3,
            "special_prediction": special, "confidence": {"F1": 0.0, "F2": 0.0, "F3": 0.0, "SPECIAL": 0.0},
            "reasoning": "Rule baseline uses frequency, gaps, observed pairs and triplets; ML is not exposed unless walk-forward validation beats this baseline.",
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")}
