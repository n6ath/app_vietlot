"""Canonical SQLite schema and an idempotent lottery_draws -> draws migration."""
import sqlite3


INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_draws_game_type ON draws (game_type)",
    "CREATE INDEX IF NOT EXISTS idx_draws_draw_number ON draws (draw_number)",
    "CREATE INDEX IF NOT EXISTS idx_draws_draw_datetime ON draws (draw_datetime)",
    "CREATE INDEX IF NOT EXISTS idx_draws_game_datetime_number ON draws (game_type, draw_datetime, draw_number)",
    # Keep the legacy names as aliases so existing query plans/tools continue
    # to work after the table rename.
    "CREATE INDEX IF NOT EXISTS idx_lottery_draws_game_type ON draws (game_type)",
    "CREATE INDEX IF NOT EXISTS idx_lottery_draws_draw_number ON draws (draw_number)",
    "CREATE INDEX IF NOT EXISTS idx_lottery_draws_draw_datetime ON draws (draw_datetime)",
    "CREATE INDEX IF NOT EXISTS idx_lottery_draws_game_datetime_number ON draws (game_type, draw_datetime, draw_number)",
)


def ensure_schema(conn: sqlite3.Connection) -> None:
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.execute("BEGIN")
    try:
        if "draws" not in tables:
            conn.execute("""CREATE TABLE draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_type TEXT NOT NULL,
                draw_number TEXT NOT NULL,
                draw_datetime TEXT NOT NULL,
                n1 INTEGER NOT NULL, n2 INTEGER NOT NULL, n3 INTEGER NOT NULL,
                n4 INTEGER NOT NULL, n5 INTEGER NOT NULL, n6 INTEGER,
                special_number INTEGER NULL,
                created_at TEXT NOT NULL, source TEXT,
                UNIQUE (game_type, draw_number)
            )""")
            if "lottery_draws" in tables:
                old = {r[1] for r in conn.execute("PRAGMA table_info(lottery_draws)")}
                cols = ["id", "game_type", "draw_number", "draw_datetime",
                        "n1", "n2", "n3", "n4", "n5", "n6",
                        "created_at", "source"]
                target = cols + ["special_number"]
                select = [c if c in old else "NULL" for c in cols]
                select.append("special_number" if "special_number" in old else "NULL")
                conn.execute(
                    f"INSERT INTO draws ({','.join(target)}) SELECT {','.join(select)} FROM lottery_draws"
                )
                conn.execute("DROP TABLE lottery_draws")
        # Older draws tables may predate special_number.
        columns = {r[1] for r in conn.execute("PRAGMA table_info(draws)")}
        if "special_number" not in columns:
            conn.execute("ALTER TABLE draws ADD COLUMN special_number INTEGER NULL")
        for statement in INDEXES:
            conn.execute(statement)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
