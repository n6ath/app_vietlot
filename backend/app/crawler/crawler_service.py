"""Crawler orchestration with immutable per-game configuration."""
from dataclasses import asdict
import csv
import re
from datetime import datetime
from pathlib import Path
import sqlite3
import requests
from bs4 import BeautifulSoup
from .crawler_535 import CONFIG as C535
from .crawler_645 import CONFIG as C645
from .crawler_655 import CONFIG as C655

CONFIGS = {c.game_type: c for c in (C535, C645, C655)}

class CrawlerService:
    def __init__(self, config=None):
        self.config = config or C645

    def build_url(self, draw_number: int) -> str:
        if draw_number < 1: raise ValueError("draw_number must be positive")
        return self.config.url_pattern.format(draw_number=f"{draw_number:05d}")

    def output_path(self, backend_dir: Path) -> Path:
        return (backend_dir / self.config.output_csv).resolve()

    def describe(self) -> dict:
        return asdict(self.config)

    def write_new_draws(self, rows, backend_dir: Path) -> int:
        """Append parsed rows, deduplicated by (game_type, draw_number)."""
        path = self.output_path(backend_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = ["game_type", "draw_number", "draw_datetime", "n1", "n2",
                  "n3", "n4", "n5", "n6", "special_number", "created_at", "source"]
        existing = set()
        if path.exists():
            with path.open(newline="", encoding="utf-8") as stream:
                existing = {(r.get("game_type"), r.get("draw_number"))
                            for r in csv.DictReader(stream)}
        pending = [r for r in rows if (self.config.game_type, str(r["draw_number"])) not in existing]
        if pending:
            with path.open("a", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                if not existing:
                    writer.writeheader()
                for row in pending:
                    writer.writerow({field: row.get(field) for field in fields})
        return len(pending)

    def crawl(self, rows=None, **kwargs):
        """Persist supplied parser output; downloading remains an explicit caller concern."""
        if rows is None:
            raise ValueError("crawl requires parsed rows (network jobs are opt-in)")
        return self.write_new_draws(rows, Path(__file__).resolve().parents[2])

    def crawl_new_draws(self, db_path: Path, backend_dir: Path, lookahead: int = 3) -> list[dict]:
        """Fetch a small forward window and return only identities absent from SQLite."""
        with sqlite3.connect(db_path) as conn:
            latest = conn.execute(
                "SELECT COALESCE(MAX(CAST(draw_number AS INTEGER)), 0) "
                "FROM draws WHERE game_type = ?",
                (self.config.game_type,),
            ).fetchone()[0]
        rows = []
        for draw_number in range(int(latest) + 1, int(latest) + lookahead + 1):
            try:
                response = requests.get(
                    self.build_url(draw_number),
                    headers={"User-Agent": "VietlottAnalytics/1.0"},
                    timeout=15,
                )
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                row = self.parse_html(response.text)
                rows.append(row)
            except (requests.RequestException, ValueError) as exc:
                print(f"[WARN] {self.config.game_type} {draw_number:05d}: {exc}")
        self.write_new_draws(rows, backend_dir)
        return rows

    def parse_html(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        number_match = re.search(r"Kỳ\s*#\s*(\d+)", text, re.IGNORECASE)
        date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
        if not number_match or not date_match:
            raise ValueError("source draw number/date missing")
        time_match = re.search(r"(\d{1,2}:\d{2})(?::(\d{2}))?", text)
        time_text = time_match.group(0) if time_match else "00:00:00"
        if time_match and time_match.group(2) is None:
            time_text += ":00"
        draw_datetime = datetime.strptime(
            f"{date_match.group(1)} {time_text}", "%d/%m/%Y %H:%M:%S"
        ).strftime("%Y-%m-%d %H:%M:%S")
        candidates = []
        for container in soup.find_all("div"):
            values = [
                span.get_text(strip=True)
                for span in container.find_all(
                    "span", class_=lambda value: value and "tabular-nums" in value
                )
            ]
            if len(values) in (self.config.main_count, self.config.main_count + 1):
                if all(re.fullmatch(r"\d{1,2}", value) for value in values):
                    candidates.append(values)
        if not candidates:
            raise ValueError("source numbers missing")
        values = [int(value) for value in max(candidates, key=len)]
        main = values[: self.config.main_count]
        if len(set(main)) != self.config.main_count or any(
            value < 1 or value > self.config.max_number for value in main
        ):
            raise ValueError("invalid main numbers")
        special = values[self.config.main_count] if len(values) > self.config.main_count else None
        if special is not None and not 1 <= special <= self.config.max_number:
            raise ValueError("invalid special number")
        row = {
            "game_type": self.config.game_type,
            "draw_number": number_match.group(1).zfill(5),
            "draw_datetime": draw_datetime,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": self.config.url_pattern.split("/")[2],
        }
        row.update({f"n{i + 1}": value for i, value in enumerate(main)})
        row["n6"] = main[5] if len(main) == 6 else None
        row["special_number"] = special if self.config.game_type == "5_35" else None
        return row
