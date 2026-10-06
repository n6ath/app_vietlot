"""Crawl Vietlott result pages for all supported game types."""

from __future__ import annotations

import csv
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GAME_TYPE = "6_45"
START_DRAW = 1565
START_DATE = "2016-07-18"
END_DATE = "2026-09-20"
OUTPUT_CSV = "data/645.csv"

GAME_CONFIG = {
    "5_35": {
        "url_pattern": "https://kqxso.top/vietlot/power535/{draw_number}",
        "main_count": 5,
        "main_max": 35,
        "has_bonus": True,
    },
    "6_45": {
        "url_pattern": "https://kqxso.top/vietlot/power645/{draw_number}",
        "main_count": 6,
        "main_max": 45,
        "has_bonus": False,
    },
    "6_55": {
        "url_pattern": "https://kqxso.top/vietlot/power655/{draw_number}",
        "main_count": 6,
        "main_max": 55,
        "has_bonus": True,
    },
}
SOURCE_NAME = "kqxso.top"
REQUEST_TIMEOUT_SECONDS = 20
REQUEST_RETRIES = 2
REQUEST_DELAY_SECONDS = 1.0
MAX_CONSECUTIVE_FAILURES = 20
CSV_FIELDNAMES = [
    "id",
    "game_type",
    "draw_number",
    "draw_datetime",
    "n1",
    "n2",
    "n3",
    "n4",
    "n5",
    "n6",
    "bonus_number",
    "created_at",
    "source",
]

BACKEND_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = (BACKEND_DIR / OUTPUT_CSV).resolve()
DEBUG_HTML_DIR = BACKEND_DIR / "data" / "crawler_debug"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


def build_draw_url(draw_number: int) -> str:
    """Build a page URL while preserving the source's five-digit draw format."""
    if draw_number < 1:
        raise ValueError("draw_number must be positive")
    try:
        pattern = GAME_CONFIG[GAME_TYPE]["url_pattern"]
    except KeyError as exc:
        raise ValueError(f"Unsupported GAME_TYPE: {GAME_TYPE}") from exc
    return pattern.format(draw_number=f"{draw_number:05d}")


def create_session() -> requests.Session:
    """Create a session with a realistic header and limited retry policy."""
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
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def fetch_page(session: requests.Session, draw_number: int) -> Response | None:
    """Fetch one HTML page, returning None for a handled page/network failure."""
    url = build_draw_url(draw_number)
    print(f"[FETCH] {url}")
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        print(f"[WARN] Draw {draw_number:05d} timed out")
        return None
    except requests.exceptions.ConnectionError as exc:
        print(f"[WARN] Draw {draw_number:05d} connection error: {exc}")
        return None
    except requests.exceptions.RequestException as exc:
        print(f"[WARN] Draw {draw_number:05d} request failed: {exc}")
        return None

    if response.status_code == 404:
        print(f"[WARN] Draw {draw_number:05d} not found | HTTP status: 404")
        return None
    if response.status_code >= 400:
        print(f"[WARN] Draw {draw_number:05d} HTTP {response.status_code}")
        return None
    if not response.text.strip():
        print(f"[WARN] Draw {draw_number:05d} returned empty HTML")
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else "<no title>"
    print(
        f"[HTTP] {response.status_code} | URL: {response.url} | "
        f"Content-Type: {response.headers.get('Content-Type', '<missing>')} | "
        f"Title: {title}"
    )
    return response


def parse_draw_number(soup: BeautifulSoup) -> str:
    """Extract the displayed draw number from text such as ``Kỳ #00890``."""
    text = soup.get_text(" ", strip=True)
    match = re.search(r"Kỳ\s*#\s*(\d+)", text, flags=re.IGNORECASE)
    if not match:
        raise ValueError("missing draw number (expected text like 'Kỳ #00890')")
    return match.group(1).zfill(5)


def parse_draw_datetime(soup: BeautifulSoup) -> str:
    """Extract the source date and optional time and normalize it for storage.

    Power 5/35 pages include a time, while the Mega 6/45 page currently exposes
    only ``Thứ Sáu, 14/08/2026`` in a ``p.text-sm.font-semibold.text-white/90``
    element. In that case the source does not provide a time, so midnight is
    used explicitly rather than inventing a draw time.
    """
    date_element = soup.select_one("p.text-sm.font-semibold.text-white\\/90")
    date_text = date_element.get_text(" ", strip=True) if date_element else soup.get_text(" ", strip=True)
    date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", date_text)
    if not date_match:
        raise ValueError("missing draw date/time")
    time_match = re.search(r"(\d{1,2}:\d{2})(?::(\d{2}))?", date_text)
    try:
        time_text = time_match.group(0) if time_match else "00:00:00"
        if time_match and time_match.group(2) is None:
            time_text += ":00"
        parsed = datetime.strptime(f"{date_match.group(1)} {time_text}", "%d/%m/%Y %H:%M:%S")
    except ValueError as exc:
        raise ValueError(f"malformed draw date/time: {date_text}") from exc
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def parse_numbers(soup: BeautifulSoup) -> tuple[list[int], int | None]:
    """Extract main and optional bonus values from the result ball area."""
    config = GAME_CONFIG.get(GAME_TYPE)
    if config is None:
        raise ValueError(f"unsupported game type: {GAME_TYPE}")
    expected_count = config["main_count"]
    max_number = config["main_max"]
    candidates: list[list[str]] = []

    for container in soup.find_all("div"):
        spans = container.find_all(
            "span", class_=lambda value: value and "tabular-nums" in value
        )
        values = [span.get_text(strip=True) for span in spans]
        if (
            len(values) in (expected_count, expected_count + 1)
            and all(re.fullmatch(r"\d{1,2}", value) for value in values)
        ):
            candidates.append(values)

    if not candidates:
        raise ValueError("missing lottery number result area")

    # Prefer the candidate that includes the configured bonus ball. This avoids
    # selecting nested containers with only a subset of the result balls.
    raw_values = max(candidates, key=len)
    if len(raw_values) < expected_count:
        raise ValueError(f"expected {expected_count} main numbers, found {len(raw_values)}")
    try:
        numbers = [int(value) for value in raw_values[:expected_count]]
        bonus = int(raw_values[expected_count]) if len(raw_values) > expected_count else None
    except ValueError as exc:
        raise ValueError("malformed lottery numbers") from exc

    if len(set(numbers)) != expected_count:
        raise ValueError(f"duplicate main numbers: {numbers}")
    if any(number < 1 or number > max_number for number in numbers):
        raise ValueError(f"main number outside 1-{max_number}: {numbers}")
    if config["has_bonus"] and bonus is not None and not (1 <= bonus <= max_number):
        raise ValueError(f"bonus number outside 1-{max_number}: {bonus}")
    if not config["has_bonus"]:
        bonus = None
    return sorted(numbers), bonus


def parse_draw_page(html: str) -> dict[str, Any]:
    """Parse and validate one result page into a CSV-ready record."""
    if not html.strip():
        raise ValueError("missing HTML")
    soup = BeautifulSoup(html, "html.parser")
    draw_number = parse_draw_number(soup)
    draw_datetime = parse_draw_datetime(soup)
    numbers, bonus = parse_numbers(soup)
    print(f"[DRAW] {draw_number}")
    print(f"[DATE] {draw_datetime}")
    print(f"[NUMBERS] {' '.join(str(number) for number in numbers)}")
    print(f"[BONUS] {bonus if bonus is not None else ''}")
    return {
        "game_type": GAME_TYPE,
        "draw_number": draw_number,
        "draw_datetime": draw_datetime,
        "n1": numbers[0],
        "n2": numbers[1],
        "n3": numbers[2],
        "n4": numbers[3],
        "n5": numbers[4],
        "n6": numbers[5] if len(numbers) == 6 else "",
        "bonus_number": bonus if bonus is not None else "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": SOURCE_NAME,
    }


def load_existing_csv(csv_path: Path) -> list[dict[str, str]]:
    """Read existing rows and reject malformed CSV structure early."""
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {csv_path}")
        required_fields = [field for field in CSV_FIELDNAMES if field != "bonus_number"]
        missing = [field for field in required_fields if field not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")
        rows = []
        for row in reader:
            if row:
                row.setdefault("bonus_number", "")
                rows.append(dict(row))
        return rows


def save_csv(records: list[dict[str, Any]], csv_path: Path) -> tuple[int, int]:
    """Merge, de-duplicate, sort chronologically, and rewrite the complete CSV."""
    existing_rows = load_existing_csv(csv_path)
    existing_keys = {
        (row.get("game_type", ""), row.get("draw_number", "")) for row in existing_rows
    }
    skipped_duplicates = 0
    new_rows: list[dict[str, Any]] = []
    for record in records:
        key = (str(record["game_type"]), str(record["draw_number"]))
        if key in existing_keys:
            skipped_duplicates += 1
            continue
        existing_keys.add(key)
        new_rows.append(record)

    all_rows = existing_rows + new_rows
    all_rows.sort(
        key=lambda row: (
            str(row.get("draw_datetime", "")),
            str(row.get("draw_number", "")),
        )
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row_id, row in enumerate(all_rows, start=1):
            writer.writerow(
                {
                    field: row_id if field == "id" else row.get(field, "")
                    for field in CSV_FIELDNAMES
                }
            )
    return skipped_duplicates, len(all_rows)


def crawl_draws(session: requests.Session) -> tuple[list[dict[str, Any]], int, int]:
    """Crawl backwards until the configured lower date bound is reached."""
    start_date = datetime.strptime(START_DATE, "%Y-%m-%d").date()
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d").date()
    current_draw = START_DRAW
    pages_requested = 0
    failed_pages = 0
    consecutive_failures = 0
    records: list[dict[str, Any]] = []

    while current_draw > 0:
        print(f"[FETCH] {current_draw:05d}")
        pages_requested += 1
        response = fetch_page(session, current_draw)
        if response is None:
            failed_pages += 1
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(
                    f"[STOP] {MAX_CONSECUTIVE_FAILURES} consecutive page failures; "
                    "stopping safely"
                )
                break
            current_draw -= 1
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        consecutive_failures = 0
        try:
            record = parse_draw_page(response.text)
            parsed_date = datetime.strptime(
                record["draw_datetime"], "%Y-%m-%d %H:%M:%S"
            ).date()
            if parsed_date < start_date:
                print("[STOP] Reached draw date older than START_DATE")
                break
            if parsed_date <= end_date:
                records.append(record)
                numbers = " ".join(
                    str(record[f"n{i}"]) for i in range(1, GAME_CONFIG[GAME_TYPE]["main_count"] + 1)
                )
                print(
                    f"[OK] {record['draw_number']} | "
                    f"{record['draw_datetime']} | {numbers} | "
                    f"bonus={record['bonus_number'] or ''}"
                )
            else:
                print(
                    f"[SKIP] {record['draw_number']} | {record['draw_datetime']} "
                    "is newer than END_DATE"
                )
        except ValueError as exc:
            failed_pages += 1
            DEBUG_HTML_DIR.mkdir(parents=True, exist_ok=True)
            debug_path = DEBUG_HTML_DIR / f"draw_{current_draw:05d}.html"
            debug_path.write_text(response.text[:3000], encoding="utf-8")
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else "<no title>"
            try:
                detected_draw_number = parse_draw_number(soup)
            except ValueError:
                detected_draw_number = "<not detected>"
            try:
                detected_datetime = parse_draw_datetime(soup)
            except ValueError:
                detected_datetime = "<not detected>"
            try:
                detected_main, detected_bonus = parse_numbers(soup)
                detected_numbers = " ".join(str(number) for number in detected_main)
                detected_numbers += f" | bonus={detected_bonus or ''}"
            except ValueError:
                detected_numbers = "<not detected>"
            print(f"[WARN] Draw {current_draw:05d} invalid page: {exc}")
            print(
                f"[DEBUG] URL: {response.url} | HTTP status: {response.status_code} | "
                f"Title: {title} | detected_draw_number={detected_draw_number} | "
                f"detected_draw_datetime={detected_datetime} | "
                f"detected_numbers={detected_numbers} | Debug HTML: {debug_path}"
            )

        current_draw -= 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return records, pages_requested, failed_pages


def main() -> None:
    """Run the crawler and print a summary."""
    print("Starting Vietlott HTML crawler")
    print(f"Game: {GAME_TYPE}")
    print(f"Start draw: {START_DRAW:05d}")
    print(f"Date range: {START_DATE} -> {END_DATE}")
    print()

    session = create_session()
    try:
        records, pages_requested, failed_pages = crawl_draws(session)
    finally:
        session.close()

    skipped_duplicates, total_csv_records = save_csv(records, OUTPUT_PATH)
    print()
    print(f"Saved {len(records) - skipped_duplicates} new records to {OUTPUT_PATH}")
    print(f"Total pages requested: {pages_requested}")
    print(f"Successful draws: {len(records)}")
    print(f"Failed draws: {failed_pages}")
    print(f"Skipped duplicates: {skipped_duplicates}")
    print(f"Total CSV records: {total_csv_records}")
    print(f"Output path: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
