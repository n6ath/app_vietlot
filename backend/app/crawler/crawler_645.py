from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    game_type: str = "6_45"
    main_count: int = 6
    max_number: int = 45
    output_csv: str = "data/645.csv"
    url_pattern: str = "https://kqxso.top/vietlot/power645/{draw_number}"

CONFIG = Config()
