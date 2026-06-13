\
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo


def normalize_signal(signal: str | None) -> str:
    if not signal:
        return "UNKNOWN"
    s = signal.strip().upper()
    if s in {"BUY", "AL", "LONG"}:
        return "BUY"
    if s in {"SELL", "SAT", "SHORT"}:
        return "SELL"
    if s in {"NEUTRAL", "BEKLE", "WAIT", "HOLD"}:
        return "NEUTRAL"
    return s


def tr_signal(signal: str | None) -> str:
    normalized = normalize_signal(signal)
    return {"BUY": "AL", "SELL": "SAT", "NEUTRAL": "NÖTR", "UNKNOWN": "YOK"}.get(normalized, normalized)


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


def build_summary_message(*, instruments: list[dict[str, Any]], states: list[dict[str, Any]], timezone_name: str) -> str:
    tz = ZoneInfo(timezone_name)
    now_str = datetime.now(tz).strftime("%d.%m.%Y %H:%M")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in states:
        grouped[(row["instrument_key"], row["timeframe"])].append(row)

    lines = [
        "📊 <b>Günlük Sinyal Özeti</b>",
        f"<b>Tarih:</b> {escape(now_str)}",
        "",
    ]

    for inst in instruments:
        key = inst["key"]
        expected_timeframe = inst.get("timeframe", "")
        rows = grouped.get((key, expected_timeframe), [])
        lines.append(f"{inst.get('emoji', '•')} <b>{escape(inst.get('name', key))}</b>")
        lines.append(f"Grafik: <b>{escape(expected_timeframe or '-')}</b>")

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
        lines.append(f"Genel durum: <b>{escape(combined_status(rows))}</b>")
        lines.append("")

    return "\n".join(lines).strip()
