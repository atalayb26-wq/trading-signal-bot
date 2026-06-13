\
from __future__ import annotations

from typing import Any

from app.indicators import calculate_all_signals
from app.market_data import fetch_ohlcv_for_instrument
from app.reporting import build_change_message
from app.settings import settings
from app.storage import SignalStorage


async def run_signal_engine_once(*, instruments: list[dict[str, Any]], storage: SignalStorage, telegram, send_change_notifications: bool = True) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for instrument in instruments:
        try:
            df = await fetch_ohlcv_for_instrument(instrument, limit=settings.market_data_lookback_bars)
            if df.empty:
                raise ValueError("Veri çekilemedi veya veri boş döndü.")

            price = float(df["close"].iloc[-1])
            bar_time = str(df.index[-1])
            signals = calculate_all_signals(df)
            item_updates = []

            for signal in signals:
                update = storage.upsert_signal(
                    instrument_key=instrument["key"],
                    display_name=instrument["name"],
                    symbol=instrument["symbol"],
                    raw_symbol=instrument.get("data_symbol"),
                    timeframe=instrument["timeframe"],
                    indicator=signal["indicator"],
                    signal=signal["signal"],
                    price=price,
                    tv_time=bar_time,
                    event_type="ENGINE_RUN",
                    raw_payload={"source":"signal_engine","instrument":instrument,"signal":signal,"last_bar_time":bar_time,"last_close":price},
                )
                item_updates.append(update)
                should_notify = send_change_notifications and (update["changed"] or (settings.notify_on_first_signal and update["first_insert"]))
                if settings.telegram_configured and should_notify:
                    await telegram.send_message(build_change_message(update))

            results.append({"instrument_key": instrument["key"], "name": instrument["name"], "timeframe": instrument["timeframe"], "provider": instrument.get("data_provider"), "data_symbol": instrument.get("data_symbol"), "last_bar_time": bar_time, "last_close": price, "updates": item_updates})
        except Exception as exc:
            errors.append({"instrument_key": instrument.get("key"), "name": instrument.get("name"), "error": str(exc)})

    return {"ok": len(errors) == 0, "updated_count": len(results), "error_count": len(errors), "results": results, "errors": errors}
