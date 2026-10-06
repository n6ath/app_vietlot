from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class Draw(BaseModel):
    id: int | None = None
    game_type: str
    draw_number: str
    draw_datetime: str
    numbers: list[int]
    special_number: int | None = None
    created_at: str | None = None
    source: str | None = None


class PaginatedDraws(BaseModel):
    results: list[Draw]
    page: int
    page_size: int
    total: int


class GameQuery(BaseModel):
    game_type: str = Field(default="6_45")


class LatestResponse(BaseModel):
    result: Draw | None


class StatisticsResponse(BaseModel):
    game_type: str
    hot_numbers: list[int]
    cold_numbers: list[int]
    overdue_numbers: list[int]
    overdue_details: list[dict[str, Any]]
    number_frequency: dict[str, int]
    monthly_frequency: dict[str, dict[int, int]]
    yearly_frequency: dict[str, dict[int, int]] = Field(default_factory=dict)
    expected_gap: float
    recent_trends: list[float]
    trend_scores: dict[int, float] = Field(default_factory=dict)
    momentum_scores: dict[int, float] = Field(default_factory=dict)


class CombinationResponse(BaseModel):
    pair: list[int] | None = None
    triplet: list[int] | None = None
    count: int
    confidence: float | None = None


class PredictionConfidence(BaseModel):
    F1: float
    F2: float
    F3: float
    SPECIAL: float


class PredictionResponse(BaseModel):
    game_type: str
    hot_numbers: list[int]
    cold_numbers: list[int]
    overdue_numbers: list[int]
    f1_prediction: list[int]
    f2_prediction: list[int]
    f3_prediction: list[int]
    special_prediction: list[int]
    confidence: PredictionConfidence
    reasoning: str
    generated_at: str
