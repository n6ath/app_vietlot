"""Crawl missing Power 5/35 special numbers for existing database draws.

This intentionally does not create lottery rows or recrawl main-number data.
It reads the existing 5_35 identities from SQLite, fetches only rows whose
special_number is NULL, and writes a small update CSV for the importer.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BACKEND_DIR = Path(__file__).resolve().parent
DB_PATH = BACKEND_DIR / "data" / "vietlot.sqlite"
OUTPUT_PATH = BACKEND_DIR / "data" / "535_special_numbers.csv"
BASE_URL = "https://kqxso.top/vietlot/power535/{draw_number}"
SOURCE_NAME = "kqxso.top"
SPECIAL_MIN = 1
SPECIAL_MAX = 35
REQUEST_TIMEOUT_SECONDS = 20
REQUEST_RETRIES = 2
REQUEST_DELAY_SECONDS = 0.35
CSV_FIELDS = [
    "game_type",
    "draw_number",
    "draw_datetime",
    "special_number",
    "source",
    "crawled_at",
]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi,en-US;q=0.8,en;q=0.6",
        }
    )
    retry = Retry(
        total=REQUEST_RETRIES,
        connect=REQUEST_RETRIES,
        read=REQUEST_RETRIES,
        status=REQUEST_RETRIES,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def load_missing_draws(conn: sqlite3.Connection) -> list[dict[str, str]]:
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(lottery_draws)")
    }
    required = {"game_type", "draw_number", "draw_datetime", "special_number"}
    if not required.issubset(columns):
        raise RuntimeError(
            "special_number migration is required before crawling missing values"
        )
    rows = conn.execute(
        """
        SELECT draw_number, draw_datetime
        FROM lottery_draws
        WHERE game_type = '5_35' AND special_number IS NULL
        ORDER BY CAST(draw_number AS INTEGER)
        """
    ).fetchall()
    return [
        {"draw_number": str(row[0]), "draw_datetime": str(row[1])}
        for row in rows
    ]


def parse_draw_number(soup: BeautifulSoup) -> str:
    match = re.search(
        r"Kỳ\s*#\s*(\d+)", soup.get_text(" ", strip=True), flags=re.IGNORECASE
    )
    if not match:
        raise ValueError("missing displayed draw number")
    return match.group(1).zfill(5)


def parse_draw_datetime(soup: BeautifulSoup) -> str:
    element = soup.select_one("p.text-sm.font-semibold.text-white\\/90")
    text = element.get_text(" ", strip=True) if element else soup.get_text(" ", strip=True)
    date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    if not date_match:
        raise ValueError("missing draw date")
    time_match = re.search(r"(\d{1,2}:\d{2})(?::(\d{2}))?", text)
    time_text = time_match.group(0) if time_match else "00:00:00"
    if time_match and time_match.group(2) is None:
        time_text += ":00"
    try:
        value = datetime.strptime(
            f"{date_match.group(1)} {time_text}", "%d/%m/%Y %H:%M:%S"
        )
    except ValueError as exc:
        raise ValueError(f"malformed draw date: {text}") from exc
    return value.strftime("%Y-%m-%d %H:%M:%S")


def parse_special_number(soup: BeautifulSoup) -> int:
    candidates: list[list[str]] = []
    for container in soup.find_all("div"):
        values = [
            span.get_text(strip=True)
            for span in container.find_all(
                "span", class_=lambda value: value and "tabular-nums" in value
            )
        ]
        if len(values) >= 6 and all(re.fullmatch(r"\d{1,2}", value) for value in values):
            candidates.append(values)
    if not candidates:
        raise ValueError("missing 5/35 result numbers")
    values = max(candidates, key=len)
    main = [int(value) for value in values[:5]]
    special = int(values[5])
    if len(set(main)) != 5 or any(number < 1 or number > 35 for number in main):
        raise ValueError(f"invalid main numbers: {main}")
    if not SPECIAL_MIN <= special <= SPECIAL_MAX:
        raise ValueError(f"special_number outside 1-{SPECIAL_MAX}: {special}")
    return special


def fetch_special(
    session: requests.Session, expected: dict[str, str]
) -> dict[str, str]:
    draw_number = expected["draw_number"].zfill(5)
    url = BASE_URL.format(draw_number=draw_number)
    print(f"[FETCH] {draw_number} {url}")
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    if not response.text.strip():
        raise ValueError("empty HTML")
    soup = BeautifulSoup(response.text, "html.parser")
    detected_number = parse_draw_number(soup)
    detected_datetime = parse_draw_datetime(soup)
    if detected_number != draw_number:
        raise ValueError(
            f"source draw mismatch: requested {draw_number}, found {detected_number}"
        )
    if detected_datetime != expected["draw_datetime"]:
        raise ValueError(
            f"source date mismatch: expected {expected['draw_datetime']}, "
            f"found {detected_datetime}"
        )
    special = parse_special_number(soup)
    print(f"[OK] {draw_number} | {detected_datetime} | special={special:02d}")
    return {
        "game_type": "5_35",
        "draw_number": draw_number,
        "draw_datetime": detected_datetime,
        "special_number": str(special),
        "source": SOURCE_NAME,
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def save_records(records: list[dict[str, str]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def crawl() -> tuple[list[dict[str, str]], list[str]]:
    with sqlite3.connect(DB_PATH) as conn:
        targets = load_missing_draws(conn)
    records: list[dict[str, str]] = []
    errors: list[str] = []
    session = create_session()
    try:
        for target in targets:
            try:
                records.append(fetch_special(session, target))
            except (requests.RequestException, ValueError) as exc:
                message = f"{target['draw_number']}: {exc}"
                errors.append(message)
                print(f"[ERROR] {message}")
            time.sleep(REQUEST_DELAY_SECONDS)
    finally:
        session.close()
    return records, errors


def main() -> None:
    print("Starting missing Power 5/35 special-number crawler")
    records, errors = crawl()
    save_records(records)
    print(f"Crawled records: {len(records)}")
    print(f"Errors: {len(errors)}")
    print(f"Output: {OUTPUT_PATH}")
    if errors:
        print("Manual review:")
        for error in errors:
            print(f"  {error}")


if __name__ == "__main__":
    main()
