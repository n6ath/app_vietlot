from fastapi import APIRouter, HTTPException, Path, Query

from .config import GAME_CONFIG
from .models import (
    CombinationResponse,
    LatestResponse,
    PaginatedDraws,
    PredictionResponse,
    StatisticsResponse,
)
from .repository import DrawRepository
from .services import (
    get_top_pairs, get_top_triplets, predict_game, statistics, validate_game,
)

router = APIRouter()
repository = DrawRepository()


def _game(game_type: str) -> str:
    try:
        return validate_game(game_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/health")
def health() -> dict[str, str]:
    try:
        repository.latest("6_45")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc
    return {"status": "ok", "database": "connected"}


@router.get("/history", response_model=PaginatedDraws)
@router.get("/draws", response_model=PaginatedDraws, include_in_schema=False)
def history(
    game_type: str = Query("6_45"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict:
    values, total = repository.list(_game(game_type), page, page_size)
    return {"results": values, "page": page, "page_size": page_size, "total": total}


@router.get("/draws/{game_type}", response_model=PaginatedDraws, include_in_schema=False)
def draw_history(
    game_type: str = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict:
    return history(game_type, page, page_size)


@router.get("/latest", response_model=LatestResponse)
def latest(game_type: str = "6_45") -> dict:
    value = repository.latest(_game(game_type))
    return {"result": value}


@router.get("/draws/{game_type}/latest", include_in_schema=False)
def draw_latest(game_type: str = Path(...)) -> dict:
    return latest(game_type)


@router.get("/statistics", response_model=StatisticsResponse)
def stats(game_type: str = Query("6_45")) -> dict:
    return statistics(_game(game_type))


@router.get("/statistics/{game_type}", include_in_schema=False)
def game_stats(game_type: str = Path(...)) -> dict:
    return stats(game_type)


@router.get("/pairs", response_model=list[CombinationResponse])
def pairs(
    game_type: str = Query("6_45"),
    lookback: int | None = Query(None, ge=1),
    top_n: int = Query(10, ge=1, le=100),
) -> list[dict]:
    return get_top_pairs(_game(game_type), lookback, top_n)


@router.get("/triplets", response_model=list[CombinationResponse])
def triplets(
    game_type: str = Query("6_45"),
    lookback: int | None = Query(None, ge=1),
    top_n: int = Query(10, ge=1, le=100),
) -> list[dict]:
    return get_top_triplets(_game(game_type), lookback, top_n)


@router.get("/prediction", response_model=PredictionResponse)
def prediction(game_type: str = "6_45") -> dict:
    return predict_game(_game(game_type))


@router.get("/prediction/{game_type}", include_in_schema=False)
def game_prediction(game_type: str = Path(...)) -> dict:
    return prediction(game_type)
