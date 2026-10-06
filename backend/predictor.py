"""Weighted scoring prediction engine for Vietlott draws."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .statistics import (
        fetch_game_draws,
        get_cold_numbers,
        get_frequency_table,
        get_hot_numbers,
        get_overdue_numbers,
    )
except ImportError:
    from statistics import (
        fetch_game_draws,
        get_cold_numbers,
        get_frequency_table,
        get_hot_numbers,
        get_overdue_numbers,
    )

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = (PROJECT_ROOT / "data" / "vietlot.sqlite").resolve()

GAME_CONFIG: dict[str, dict[str, int]] = {
    "5_35": {"max_number": 35, "numbers_per_draw": 5},
    "6_45": {"max_number": 45, "numbers_per_draw": 6},
    "6_55": {"max_number": 55, "numbers_per_draw": 6},
}


@dataclass(frozen=True)
class PredictionInput:
    game_type: str
    lookback_hot: int = 20
    lookback_cold: int = 100
    lookback_pairs: int = 50
    lookback_recent: int = 20
    top_n: int = 10


class Predictor:
    """Weighted score predictor with multiple output strategies."""

    def __init__(self, game_type: str) -> None:
        if game_type not in GAME_CONFIG:
            raise ValueError(f"Unsupported game_type: {game_type}")
        self.game_type = game_type
        self.max_number = GAME_CONFIG[game_type]["max_number"]
        self.numbers_per_draw = GAME_CONFIG[game_type]["numbers_per_draw"]

    def _normalize(self, values: list[float]) -> list[float]:
        if not values:
            return []
        minimum = min(values)
        maximum = max(values)
        if maximum == minimum:
            return [1.0 for _ in values]
        return [(value - minimum) / (maximum - minimum) for value in values]

    def _number_score(self, number: int, metrics: dict[str, dict[str, float]]) -> float:
        overdue = metrics["overdue"].get(number, 0.0)
        hot = metrics["hot"].get(number, 0.0)
        frequency = metrics["frequency"].get(number, 0.0)
        pair = metrics["pair"].get(number, 0.0)
        trend = metrics["trend"].get(number, 0.0)
        return (
            0.40 * overdue
            + 0.25 * hot
            + 0.15 * frequency
            + 0.10 * pair
            + 0.10 * trend
        )

    def _build_metrics(self) -> dict[str, dict[int, float]]:
        overdue_rows = get_overdue_numbers(self.game_type)
        lifetime_rows = get_frequency_table(self.game_type)
        hot_numbers = get_hot_numbers(self.game_type, lookback=20, top_n=20)
        overdue_map = {int(item["number"]): float(item["overdue_ratio"]) for item in overdue_rows}
        frequency_map = {int(item["number"]): float(item["count"]) for item in lifetime_rows}
        hot_map = {number: 1.0 for number in hot_numbers}
        pair_map: dict[int, float] = defaultdict(float)

        # Pair score approximated by frequency table + overdue contribution.
        for item in overdue_rows:
            pair_map[int(item["number"])] = float(item["overdue_ratio"])

        trend_map: dict[int, float] = defaultdict(float)
        recent_draws = [
            number
            for draw in fetch_game_draws(self.game_type)[-20:]
            for number in draw["numbers"]
        ]
        counts = defaultdict(int)
        for value in recent_draws:
            counts[int(value)] += 1
        for number in range(1, self.max_number + 1):
            trend_map[number] = float(counts.get(number, 0))

        for number in range(1, self.max_number + 1):
            if number not in hot_map:
                hot_map[number] = 0.0
        def normalize_map(values: dict[int, float]) -> dict[int, float]:
            keys = list(range(1, self.max_number + 1))
            normalized = self._normalize([values.get(key, 0.0) for key in keys])
            return dict(zip(keys, normalized))

        return {
            "overdue": normalize_map(overdue_map),
            "hot": {number: float(1 if number in hot_numbers else 0) for number in range(1, self.max_number + 1)},
            "frequency": normalize_map(frequency_map),
            "pair": normalize_map(pair_map),
            "trend": normalize_map(trend_map),
        }

    def _get_prediction_set(self, strategy: str, top_n: int = 10) -> list[int]:
        metrics = self._build_metrics()
        scored: list[tuple[float, int]] = []
        for number in range(1, self.max_number + 1):
            if strategy == "f1":
                score = (
                    0.40 * metrics["overdue"].get(number, 0.0)
                    + 0.25 * metrics["hot"].get(number, 0.0)
                    + 0.15 * metrics["frequency"].get(number, 0.0)
                    + 0.10 * metrics["pair"].get(number, 0.0)
                    + 0.10 * metrics["trend"].get(number, 0.0)
                )
            elif strategy == "f2":
                score = (
                    0.70 * metrics["overdue"].get(number, 0.0)
                    + 0.15 * metrics["hot"].get(number, 0.0)
                    + 0.10 * metrics["frequency"].get(number, 0.0)
                    + 0.05 * metrics["trend"].get(number, 0.0)
                )
            elif strategy == "f3":
                score = (
                    0.45 * metrics["trend"].get(number, 0.0)
                    + 0.25 * metrics["hot"].get(number, 0.0)
                    + 0.15 * metrics["frequency"].get(number, 0.0)
                    + 0.10 * metrics["pair"].get(number, 0.0)
                    + 0.05 * metrics["overdue"].get(number, 0.0)
                )
            else:
                score = 0.0
            scored.append((score, number))

        ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
        return [number for _, number in ranked[:top_n]]

    def predict(self) -> dict[str, Any]:
        f1 = self._get_prediction_set("f1", top_n=self.numbers_per_draw)
        f2 = self._get_prediction_set("f2", top_n=self.numbers_per_draw)
        f3 = self._get_prediction_set("f3", top_n=self.numbers_per_draw)

        hot = get_hot_numbers(self.game_type, lookback=20, top_n=2)
        overdue = [int(item["number"]) for item in get_overdue_numbers(self.game_type)[:2]]
        trend = self._get_prediction_set("f3", top_n=1)
        wildcard_s = self._get_prediction_set("f1", top_n=1)

        special_nums = hot + overdue + trend + wildcard_s
        special_nums = list(dict.fromkeys(number for number in special_nums if number is not None))[: self.numbers_per_draw]

        return {
            "game_type": self.game_type,
            "hot_numbers": hot,
            "cold_numbers": get_cold_numbers(self.game_type, lookback=100, top_n=10),
            "overdue_numbers": overdue,
            "f1_prediction": f1,
            "f2_prediction": f2,
            "f3_prediction": f3,
            "special_prediction": special_nums,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }


def predict_game(game_type: str) -> dict[str, Any]:
    return Predictor(game_type).predict()


if __name__ == "__main__":
    for game in ("5_35", "6_45", "6_55"):
        print(json.dumps(predict_game(game), indent=2))
