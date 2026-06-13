\
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SignalStorage:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_key TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    raw_symbol TEXT,
                    timeframe TEXT NOT NULL,
                    indicator TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    price REAL,
                    tv_time TEXT,
                    received_at TEXT NOT NULL,
                    last_event_type TEXT,
                    raw_payload TEXT,
                    UNIQUE(instrument_key, timeframe, indicator)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_key TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    raw_symbol TEXT,
                    timeframe TEXT NOT NULL,
                    indicator TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    previous_signal TEXT,
                    changed INTEGER NOT NULL,
                    price REAL,
                    tv_time TEXT,
                    received_at TEXT NOT NULL,
                    event_type TEXT,
                    raw_payload TEXT
                );
                """
            )
            self._conn.commit()

    def upsert_signal(
        self,
        *,
        instrument_key: str,
        display_name: str,
        symbol: str,
        raw_symbol: str | None,
        timeframe: str,
        indicator: str,
        signal: str,
        price: float | None,
        tv_time: str | None,
        event_type: str | None,
        raw_payload: dict[str, Any],
    ) -> dict[str, Any]:
        signal = signal.upper().strip()
        indicator = indicator.strip()
        received_at = utc_now_iso()
        raw_payload_json = json.dumps(raw_payload, ensure_ascii=False, separators=(",", ":"))

        with self._lock:
            previous_row = self._conn.execute(
                "SELECT signal FROM signal_states WHERE instrument_key = ? AND timeframe = ? AND indicator = ?",
                (instrument_key, timeframe, indicator),
            ).fetchone()

            previous_signal = previous_row["signal"] if previous_row else None
            changed = previous_signal is not None and previous_signal != signal
            first_insert = previous_signal is None

            self._conn.execute(
                """
                INSERT INTO signal_states (
                    instrument_key, display_name, symbol, raw_symbol, timeframe, indicator,
                    signal, price, tv_time, received_at, last_event_type, raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_key, timeframe, indicator)
                DO UPDATE SET
                    display_name = excluded.display_name,
                    symbol = excluded.symbol,
                    raw_symbol = excluded.raw_symbol,
                    signal = excluded.signal,
                    price = excluded.price,
                    tv_time = excluded.tv_time,
                    received_at = excluded.received_at,
                    last_event_type = excluded.last_event_type,
                    raw_payload = excluded.raw_payload;
                """,
                (instrument_key, display_name, symbol, raw_symbol, timeframe, indicator, signal, price, tv_time, received_at, event_type, raw_payload_json),
            )

            self._conn.execute(
                """
                INSERT INTO signal_history (
                    instrument_key, display_name, symbol, raw_symbol, timeframe, indicator,
                    signal, previous_signal, changed, price, tv_time, received_at, event_type, raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (instrument_key, display_name, symbol, raw_symbol, timeframe, indicator, signal, previous_signal, 1 if changed else 0, price, tv_time, received_at, event_type, raw_payload_json),
            )
            self._conn.commit()

        return {
            "instrument_key": instrument_key,
            "display_name": display_name,
            "symbol": symbol,
            "raw_symbol": raw_symbol,
            "timeframe": timeframe,
            "indicator": indicator,
            "signal": signal,
            "previous_signal": previous_signal,
            "changed": changed,
            "first_insert": first_insert,
            "price": price,
            "tv_time": tv_time,
            "received_at": received_at,
            "event_type": event_type,
        }

    def latest_states(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM signal_states ORDER BY instrument_key, timeframe, indicator").fetchall()
        return [dict(row) for row in rows]

    def history(self, *, limit: int = 100, instrument_key: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        if instrument_key:
            rows = self._conn.execute(
                "SELECT * FROM signal_history WHERE instrument_key = ? ORDER BY id DESC LIMIT ?",
                (instrument_key, limit),
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM signal_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
