\
from __future__ import annotations

import hmac
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Request
from zoneinfo import ZoneInfo

from app.instruments import InstrumentRegistry
from app.reporting import build_change_message, build_summary_message, normalize_signal
from app.settings import settings
from app.storage import SignalStorage
from app.telegram_client import TelegramClient


def get_any(payload: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return default


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def require_admin(request: Request) -> None:
    if not settings.admin_configured:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN tanımlı değil.")
    token = request.headers.get("X-Admin-Token", "")
    if not hmac.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Geçersiz admin token.")


async def send_daily_summary(app: FastAPI) -> None:
    storage: SignalStorage = app.state.storage
    instruments: InstrumentRegistry = app.state.instruments
    telegram: TelegramClient = app.state.telegram

    message = build_summary_message(
        instruments=instruments.ordered(),
        states=storage.latest_states(),
        timezone_name=settings.app_timezone,
    )
    await telegram.send_message(message)


app = FastAPI(
    title="Trading Signal Telegram Bot",
    version="1.0.0",
    description="TradingView webhook alır, AlphaTrend/SuperTrend sinyallerini saklar ve Telegram'a raporlar.",
)


@app.on_event("startup")
async def startup() -> None:
    app.state.storage = SignalStorage(settings.database_path)
    app.state.instruments = InstrumentRegistry("config/instruments.json")
    app.state.telegram = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)

    scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.app_timezone))
    app.state.scheduler = scheduler

    if settings.enable_daily_summary:
        scheduler.add_job(
            send_daily_summary,
            CronTrigger(
                hour=settings.report_hour,
                minute=settings.report_minute,
                timezone=ZoneInfo(settings.app_timezone),
            ),
            args=[app],
            id="daily-summary",
            replace_existing=True,
            misfire_grace_time=300,
        )
        scheduler.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    scheduler: AsyncIOScheduler | None = getattr(app.state, "scheduler", None)
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "telegram_configured": settings.telegram_configured,
        "webhook_configured": settings.webhook_configured,
        "daily_summary_enabled": settings.enable_daily_summary,
        "timezone": settings.app_timezone,
        "report_time": f"{settings.report_hour:02d}:{settings.report_minute:02d}",
    }


@app.post("/webhook/tradingview")
async def tradingview_webhook(request: Request) -> dict[str, Any]:
    payload = await request.json()

    received_secret = str(get_any(payload, ("secret", "webhookSecret", "token"), ""))
    if not settings.webhook_configured:
        raise HTTPException(status_code=503, detail="WEBHOOK_SECRET tanımlı değil.")
    if not hmac.compare_digest(received_secret, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Geçersiz webhook secret.")

    raw_symbol = str(get_any(payload, ("symbol", "ticker", "tickerid"), "UNKNOWN"))
    timeframe = str(get_any(payload, ("timeframe", "interval", "tf"), ""))
    price = parse_float(get_any(payload, ("price", "close", "lastPrice")))
    tv_time = str(get_any(payload, ("time", "barTime", "barTimeUnix", "t"), "")) or None
    event_type = str(get_any(payload, ("eventType", "event_type", "event"), "UNKNOWN")).upper()

    registry: InstrumentRegistry = app.state.instruments
    instrument = registry.resolve(raw_symbol, timeframe)

    symbol = instrument.get("symbol") or raw_symbol
    instrument_key = instrument["key"]
    display_name = instrument.get("name") or raw_symbol

    candidate_updates: list[tuple[str, str]] = []

    alpha_signal = get_any(payload, ("alphaTrendSignal", "alpha_signal", "alphaTrend", "alpha"))
    super_signal = get_any(payload, ("superTrendSignal", "super_signal", "superTrend", "super"))

    if alpha_signal:
        candidate_updates.append(("AlphaTrend", normalize_signal(str(alpha_signal))))
    if super_signal:
        candidate_updates.append(("SuperTrend", normalize_signal(str(super_signal))))

    # Alternatif payload formatı:
    # {"indicator": "AlphaTrend", "signal": "BUY"}
    indicator = get_any(payload, ("indicator", "indicatorName"))
    signal = get_any(payload, ("signal", "side"))
    if indicator and signal and not candidate_updates:
        candidate_updates.append((str(indicator), normalize_signal(str(signal))))

    if not candidate_updates:
        raise HTTPException(
            status_code=422,
            detail="Payload içinde alphaTrendSignal/superTrendSignal veya indicator+signal bulunamadı.",
        )

    storage: SignalStorage = app.state.storage
    telegram: TelegramClient = app.state.telegram

    updates: list[dict[str, Any]] = []
    sent_messages: list[dict[str, Any]] = []

    for indicator_name, normalized_signal in candidate_updates:
        update = storage.upsert_signal(
            instrument_key=instrument_key,
            display_name=display_name,
            symbol=symbol,
            raw_symbol=raw_symbol,
            timeframe=timeframe,
            indicator=indicator_name,
            signal=normalized_signal,
            price=price,
            tv_time=tv_time,
            event_type=event_type,
            raw_payload=payload,
        )
        updates.append(update)

        is_snapshot = event_type == "BAR_CLOSE"
        should_notify_change = update["changed"] or (settings.notify_on_first_signal and update["first_insert"])
        should_notify_snapshot = settings.notify_on_bar_close_snapshot and is_snapshot

        if settings.telegram_configured and (should_notify_change or should_notify_snapshot):
            text = build_change_message(update)
            result = await telegram.send_message(text)
            sent_messages.append({"indicator": indicator_name, "telegram_ok": bool(result.get("ok"))})

    return {
        "ok": True,
        "instrument_key": instrument_key,
        "display_name": display_name,
        "raw_symbol": raw_symbol,
        "timeframe": timeframe,
        "event_type": event_type,
        "updates": updates,
        "telegram_messages": sent_messages,
    }


@app.post("/telegram/test")
async def telegram_test(request: Request) -> dict[str, Any]:
    require_admin(request)
    telegram: TelegramClient = app.state.telegram
    result = await telegram.send_message("✅ <b>Trading Signal Bot test mesajı başarılı.</b>")
    return {"ok": True, "telegram_response": result}


@app.post("/summary/send-now")
async def send_summary_now(request: Request) -> dict[str, Any]:
    require_admin(request)
    await send_daily_summary(app)
    return {"ok": True}


@app.get("/signals/latest")
async def latest_signals(request: Request) -> dict[str, Any]:
    require_admin(request)
    storage: SignalStorage = app.state.storage
    return {"ok": True, "items": storage.latest_states()}


@app.get("/signals/history")
async def signal_history(request: Request, limit: int = 100, instrument_key: str | None = None) -> dict[str, Any]:
    require_admin(request)
    storage: SignalStorage = app.state.storage
    return {"ok": True, "items": storage.history(limit=limit, instrument_key=instrument_key)}
