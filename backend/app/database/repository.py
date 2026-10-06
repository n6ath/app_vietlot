"""Repository for the canonical draws table."""
from typing import Any
from ..config import GAME_CONFIG
from .connection import connection


class DrawRepository:
    def _columns(self, conn: Any) -> list[str]:
        return [f"n{i}" for i in range(1, 7)
                if f"n{i}" in {r["name"] for r in conn.execute("PRAGMA table_info(draws)") }]

    def list(self, game_type: str, page: int = 1, page_size: int = 50):
        if game_type not in GAME_CONFIG:
            raise ValueError(f"Unsupported game_type: {game_type}")
        page, page_size = max(1, page), min(200, max(1, page_size))
        with connection() as conn:
            numbers = self._columns(conn)
            total = conn.execute("SELECT COUNT(*) FROM draws WHERE game_type=?", (game_type,)).fetchone()[0]
            fields = ", ".join(numbers)
            rows = conn.execute(
                f"SELECT id,game_type,draw_number,draw_datetime,{fields},special_number,created_at,source "
                "FROM draws WHERE game_type=? ORDER BY draw_datetime DESC, CAST(draw_number AS INTEGER) DESC LIMIT ? OFFSET ?",
                (game_type, page_size, (page - 1) * page_size)).fetchall()
        return [self._draw(row, numbers) for row in rows], int(total)

    def upsert(self, draw: dict[str, Any]) -> None:
        """Insert one draw without replacing an existing game/draw key."""
        values = [draw.get(f"n{i}") for i in range(1, 7)]
        with connection() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO draws
                (game_type,draw_number,draw_datetime,n1,n2,n3,n4,n5,n6,
                 special_number,created_at,source)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                [draw["game_type"], str(draw["draw_number"]), draw["draw_datetime"],
                 *values, draw.get("special_number"), draw.get("created_at", ""),
                 draw.get("source")])

    @staticmethod
    def _draw(row: Any, numbers: list[str]) -> dict[str, Any]:
        return {"id": row["id"], "game_type": row["game_type"],
                "draw_number": str(row["draw_number"]), "draw_datetime": row["draw_datetime"],
                "numbers": [int(row[n]) for n in numbers if row[n] is not None],
                "special_number": row["special_number"], "created_at": row["created_at"],
                "source": row["source"]}

    def latest(self, game_type: str):
        rows, _ = self.list(game_type, 1, 1)
        return rows[0] if rows else None
