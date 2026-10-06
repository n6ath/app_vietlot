from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    game_type: str = "5_35"
    main_count: int = 5
    max_number: int = 35
    output_csv: str = "data/535.csv"
    url_pattern: str = "https://kqxso.top/vietlot/power535/{draw_number}"

CONFIG = Config()
