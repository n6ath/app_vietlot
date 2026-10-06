"""Unified analytics and prediction service facade."""
from .config import GAME_CONFIG

from .predictor import predict_game
from .statistics import (
    fetch_game_draws,
    get_cold_numbers,
    get_expected_gap,
    get_frequency_table,
    get_hot_numbers,
    get_monthly_frequency,
    get_momentum,
    get_overdue_numbers,
    get_top_pairs,
    get_top_triplets,
    get_trends,
    get_yearly_frequency,
)


def validate_game(game_type: str) -> str:
    if game_type not in GAME_CONFIG:
        raise ValueError(f"Unsupported game_type: {game_type}")
    return game_type


def statistics(game_type: str) -> dict:
    validate_game(game_type)
    frequency = get_frequency_table(game_type)
    overdue = get_overdue_numbers(game_type)
    return {
        "game_type": game_type,
        "hot_numbers": get_hot_numbers(game_type),
        "cold_numbers": get_cold_numbers(game_type),
        "overdue_numbers": [item["number"] for item in overdue],
        "overdue_details": overdue,
        "number_frequency": {str(item["number"]): item["count"] for item in frequency},
        "monthly_frequency": get_monthly_frequency(game_type),
        "yearly_frequency": get_yearly_frequency(game_type),
        "expected_gap": get_expected_gap(game_type),
        "recent_trends": [
            float(len(draw["numbers"])) for draw in fetch_game_draws(game_type, limit=20)
        ],
        "trend_scores": get_trends(game_type),
        "momentum_scores": get_momentum(game_type),
    }
