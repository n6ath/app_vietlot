from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "vietlot.sqlite"
GAME_CONFIG = {
    "5_35": {"max_number": 35, "numbers_per_draw": 5},
    "6_45": {"max_number": 45, "numbers_per_draw": 6},
    "6_55": {"max_number": 55, "numbers_per_draw": 6},
}

