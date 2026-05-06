from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

_DB_PATH = Path.home() / ".config" / "mfp-mcp" / "cache.db"


class CacheStore:
    def __init__(self, path: Path = _DB_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )

    def get(self, key: str):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        data, expires_at = row
        if time.time() > expires_at:
            return None
        return json.loads(data)

    def set(self, key: str, value, ttl: float) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, data, expires_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time() + ttl),
            )

    def delete(self, key: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))

    def clear(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM cache")

    def stats(self) -> dict:
        now = time.time()
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            valid = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE expires_at > ?", (now,)
            ).fetchone()[0]
        return {"total_entries": total, "valid": valid, "expired": total - valid, "db": str(self._path)}
