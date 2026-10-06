from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    game_type: str = "6_55"
    main_count: int = 6
    max_number: int = 55
    output_csv: str = "data/655.csv"
    url_pattern: str = "https://kqxso.top/vietlot/power655/{draw_number}"

CONFIG = Config()
