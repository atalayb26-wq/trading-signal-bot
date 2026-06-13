\
from __future__ import annotations

import httpx
import pandas as pd

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def _range_for_interval(interval: str) -> str:
    if interval in {"1wk", "1mo"}:
        return "10y"
    return "2y"


def _clean_ohlcv(df: pd.DataFrame, limit: int = 350) -> pd.DataFrame:
    if df.empty:
        return df

    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[["open", "high", "low", "close", "volume"]].copy()
    df = df.dropna(subset=["open", "high", "low", "close"])
    if limit and len(df) > limit:
        df = df.tail(limit)
    return df


async def fetch_yahoo_chart_ohlcv(symbol: str, interval: str, limit: int = 350) -> pd.DataFrame:
    params = {
        "range": _range_for_interval(interval),
        "interval": interval,
        "includePrePost": "false",
        "events": "history",
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
    }

    url = YAHOO_CHART_URL.format(symbol=symbol)

    async with httpx.AsyncClient(timeout=25.0, headers=headers, follow_redirects=True) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    chart = payload.get("chart", {})
    error = chart.get("error")
    if error:
        raise ValueError(f"Yahoo chart error for {symbol}: {error}")

    results = chart.get("result") or []
    if not results:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]

    if not timestamps or not quote:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame({
        "datetime": pd.to_datetime(timestamps, unit="s", utc=True),
        "open": quote.get("open", []),
        "high": quote.get("high", []),
        "low": quote.get("low", []),
        "close": quote.get("close", []),
        "volume": quote.get("volume", [0] * len(timestamps)),
    })

    df = df.set_index("datetime")
    return _clean_ohlcv(df, limit=limit)


async def fetch_yahoo_ratio_ohlcv(
    numerator_symbol: str,
    denominator_symbol: str,
    interval: str,
    limit: int = 350,
) -> pd.DataFrame:
    numerator = await fetch_yahoo_chart_ohlcv(numerator_symbol, interval, limit=limit)
    denominator = await fetch_yahoo_chart_ohlcv(denominator_symbol, interval, limit=limit)

    if numerator.empty or denominator.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    joined = numerator.join(denominator, how="inner", lsuffix="_num", rsuffix="_den")
    if joined.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    out = pd.DataFrame(index=joined.index)
    out["open"] = joined["open_num"] / joined["open_den"]
    out["high"] = joined["high_num"] / joined["high_den"]
    out["low"] = joined["low_num"] / joined["low_den"]
    out["close"] = joined["close_num"] / joined["close_den"]
    out["volume"] = joined["volume_num"].fillna(0)
    return _clean_ohlcv(out, limit=limit)


async def fetch_ohlcv_for_instrument(instrument: dict, limit: int = 350) -> pd.DataFrame:
    provider = instrument.get("data_provider")
    interval = instrument.get("engine_interval") or ("1wk" if instrument.get("timeframe") == "1W" else "1d")

    if provider == "yahoo_chart":
        return await fetch_yahoo_chart_ohlcv(instrument["data_symbol"], interval, limit=limit)

    if provider == "yahoo_ratio":
        return await fetch_yahoo_ratio_ohlcv(
            instrument["numerator_symbol"],
            instrument["denominator_symbol"],
            interval,
            limit=limit,
        )

    raise ValueError(f"Desteklenmeyen data_provider: {provider}")
