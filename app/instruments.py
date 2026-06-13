\
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().upper().replace(" ", "")


class InstrumentRegistry:
    def __init__(self, config_path: str | Path = "config/instruments.json") -> None:
        self.config_path = Path(config_path)
        self.instruments: list[dict[str, Any]] = []
        self._alias_to_key: dict[str, str] = {}
        self._by_key: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        instruments = raw.get("instruments", raw if isinstance(raw, list) else [])
        self.instruments = instruments
        self._alias_to_key = {}
        self._by_key = {}

        for item in instruments:
            key = str(item["key"])
            self._by_key[key] = item
            aliases = set(item.get("aliases", []))
            aliases.add(item.get("data_symbol", ""))
            aliases.add(item.get("symbol", ""))
            aliases.add(key)
            for alias in aliases:
                normalized = _norm(alias)
                if normalized:
                    self._alias_to_key[normalized] = key

    def resolve(self, symbol: str | None, timeframe: str | None = None) -> dict[str, Any]:
        normalized = _norm(symbol)
        key = self._alias_to_key.get(normalized)
        if key is None and ":" in normalized:
            key = self._alias_to_key.get(normalized.split(":", 1)[1])
        if key is not None:
            instrument = dict(self._by_key[key])
            instrument["resolved"] = True
            return instrument
        return {
            "key": f"{normalized or 'UNKNOWN'}_{_norm(timeframe) or 'NA'}",
            "name": symbol or "Bilinmeyen Enstrüman",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe or "",
            "emoji": "•",
            "resolved": False,
        }

    def ordered(self) -> list[dict[str, Any]]:
        return list(self.instruments)
