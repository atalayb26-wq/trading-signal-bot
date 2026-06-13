\
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo


BUY_VALUES = {"BUY", "AL", "LONG"}
SELL_VALUES = {"SELL", "SAT", "SHORT"}


def normalize_signal(signal: str | None) -> str:
    if not signal:
        return "UNKNOWN"

    s = signal.strip().upper()
    if s in BUY_VALUES:
        return "BUY"
    if s in SELL_VALUES:
        return "SELL"
    if s in {"NEUTRAL", "BEKLE", "WAIT", "HOLD"}:
        return "NEUTRAL"
    return s


def tr_signal(signal: str | None) -> str:
    normalized = normalize_signal(signal)
    if normalized == "BUY":
        return "AL"
    if normalized == "SELL":
        return "SAT"
    if normalized == "NEUTRAL":
        return "NÖTR"
    if normalized == "UNKNOWN":
        return "YOK"
    return normalized


def format_price(price: Any) -> str:
    if price is None:
        return "-"
    try:
        value = float(price)
    except (TypeError, ValueError):
        return str(price)

    if value >= 1000:
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:,.4f}"
    return f"{value:,.8f}"


def combined_status(states: list[dict[str, Any]]) -> str:
    if not states:
        return "Veri yok"

    signals = {normalize_signal(row.get("signal")) for row in states}
    if signals == {"BUY"}:
        return "Güçlü AL"
    if signals == {"SELL"}:
        return "Güçlü SAT"
    if "BUY" in signals and "SELL" in signals:
        return "Karışık"
    if "BUY" in signals:
        return "AL ağırlıklı"
    if "SELL" in signals:
        return "SAT ağırlıklı"
    return "Nötr / Veri yok"


def build_change_message(update: dict[str, Any]) -> str:
    previous = tr_signal(update.get("previous_signal"))
    current = tr_signal(update.get("signal"))
    name = escape(update.get("display_name") or update.get("symbol") or "-")
    indicator = escape(update.get("indicator") or "-")
    timeframe = escape(update.get("timeframe") or "-")
    price = format_price(update.get("price"))

    previous_line = f"{previous} → {current}" if update.get("previous_signal") else f"İlk kayıt: {current}"

    return (
        "🚨 <b>Yeni Sinyal</b>\n\n"
        f"<b>Enstrüman:</b> {name}\n"
        f"<b>Grafik:</b> {timeframe}\n"
        f"<b>İndikatör:</b> {indicator}\n"
        f"<b>Sinyal:</b> {previous_line}\n"
        f"<b>Fiyat:</b> {escape(price)}"
    )


def build_summary_message(
    *,
    instruments: list[dict[str, Any]],
    states: list[dict[str, Any]],
    timezone_name: str,
) -> str:
    tz = ZoneInfo(timezone_name)
    now_str = datetime.now(tz).strftime("%d.%m.%Y %H:%M")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in states:
        grouped[(row["instrument_key"], row["timeframe"])].append(row)

    lines: list[str] = []
    lines.append(f"📊 <b>Günlük Sinyal Özeti</b>")
    lines.append(f"<b>Tarih:</b> {escape(now_str)}")
    lines.append("")

    used_keys: set[tuple[str, str]] = set()

    for inst in instruments:
        key = inst["key"]
        expected_timeframe = inst.get("timeframe", "")
        group_key = (key, expected_timeframe)
        rows = grouped.get(group_key, [])
        used_keys.add(group_key)

        emoji = inst.get("emoji", "•")
        name = escape(inst.get("name", key))
        timeframe = escape(expected_timeframe or "-")
        status = escape(combined_status(rows))

        lines.append(f"{emoji} <b>{name}</b>")
        lines.append(f"Grafik: <b>{timeframe}</b>")
        if not rows:
            lines.append("AlphaTrend: YOK")
            lines.append("SuperTrend: YOK")
            lines.append("Genel durum: Veri yok")
            lines.append("")
            continue

        by_indicator = {row["indicator"]: row for row in rows}
        for indicator in ("AlphaTrend", "SuperTrend"):
            row = by_indicator.get(indicator)
            sig = tr_signal(row.get("signal")) if row else "YOK"
            price = format_price(row.get("price")) if row else "-"
            lines.append(f"{escape(indicator)}: <b>{escape(sig)}</b> | Fiyat: {escape(price)}")

        lines.append(f"Genel durum: <b>{status}</b>")
        lines.append("")

    # Konfigürasyonda olmayan ama webhook'tan gelen enstrümanları da sonda göster.
    for group_key, rows in grouped.items():
        if group_key in used_keys:
            continue
        first = rows[0]
        name = escape(first.get("display_name") or first.get("symbol") or group_key[0])
        timeframe = escape(group_key[1])
        lines.append(f"• <b>{name}</b>")
        lines.append(f"Grafik: <b>{timeframe}</b>")
        for row in rows:
            lines.append(f"{escape(row['indicator'])}: <b>{escape(tr_signal(row['signal']))}</b>")
        lines.append(f"Genel durum: <b>{escape(combined_status(rows))}</b>")
        lines.append("")

    return "\n".join(lines).strip()
