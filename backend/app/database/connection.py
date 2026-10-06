import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator

from ..config import DATABASE_PATH
from .schema import ensure_schema


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
