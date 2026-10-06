"""Optional explicit data refresh utility; API startup never downloads data."""
import argparse
from pathlib import Path

from app.database.schema import ensure_schema
from app.database.connection import get_connection
from app.config import DATABASE_PATH
from app.crawler.crawler_service import CrawlerService, CONFIGS


def update_data(crawl: bool = False) -> None:
    with get_connection() as conn:
        ensure_schema(conn)
    if not crawl:
        print("Database schema verified; network crawling was not requested.")
        return
    backend_dir = Path(__file__).resolve().parent
    total = 0
    for game_type in ("5_35", "6_45", "6_55"):
        rows = CrawlerService(CONFIGS[game_type]).crawl_new_draws(
            DATABASE_PATH, backend_dir
        )
        print(f"{game_type}: new draws: {len(rows)}")
        with get_connection() as conn:
            for row in rows:
                conn.execute(
                    """INSERT OR IGNORE INTO draws
                    (game_type,draw_number,draw_datetime,n1,n2,n3,n4,n5,n6,
                     special_number,created_at,source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        row["game_type"], row["draw_number"], row["draw_datetime"],
                        row.get("n1"), row.get("n2"), row.get("n3"), row.get("n4"),
                        row.get("n5"), row.get("n6"), row.get("special_number"),
                        row["created_at"], row["source"],
                    ),
                )
        total += len(rows)
    print(f"Database updated successfully; new draws: {total}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--crawl", action="store_true", help="fetch newest source pages")
    update_data(parser.parse_args().crawl)
