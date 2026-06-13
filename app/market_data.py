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
    df = df.sort_index()

    if limit and len(df) > limit:
        df = df.tail(limit)
    return df


def _resample_daily_to_weekly(df: pd.DataFrame, limit: int = 350) -> pd.DataFrame:
    if df.empty:
        return df

    weekly = pd.DataFrame()
    weekly["open"] = df["open"].resample("W-FRI").first()
    weekly["high"] = df["high"].resample("W-FRI").max()
    weekly["low"] = df["low"].resample("W-FRI").min()
    weekly["close"] = df["close"].resample("W-FRI").last()
    weekly["volume"] = df["volume"].resample("W-FRI").sum()
    weekly = weekly.dropna(subset=["open", "high", "low", "close"])

    if limit and len(weekly) > limit:
        weekly = weekly.tail(limit)
    return weekly


async def fetch_yahoo_chart_ohlcv(symbol: str, interval: str, limit: int = 350, *, range_override: str | None = None) -> pd.DataFrame:
    params = {
        "range": range_override or _range_for_interval(interval),
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

    row_count = len(timestamps)

    df = pd.DataFrame({
        "datetime": pd.to_datetime(timestamps, unit="s", utc=True),
        "open": quote.get("open", [None] * row_count),
        "high": quote.get("high", [None] * row_count),
        "low": quote.get("low", [None] * row_count),
        "close": quote.get("close", [None] * row_count),
        "volume": quote.get("volume", [0] * row_count),
    })

    df = df.set_index("datetime")
    return _clean_ohlcv(df, limit=limit)


async def fetch_yahoo_ratio_ohlcv(
    numerator_symbol: str,
    denominator_symbol: str,
    interval: str,
    limit: int = 350,
) -> pd.DataFrame:
    # BIST ve kur haftalık timestamp'leri Yahoo'da birebir çakışmayabiliyor.
    # Bu yüzden sentetik oranı önce günlük veriden hesaplayıp sonra haftalığa çeviriyoruz.
    # XU100/USD = XU100.IS / TRY=X
    daily_limit = max(limit * 7, 2500) if interval in {"1wk", "1mo"} else limit

    numerator = await fetch_yahoo_chart_ohlcv(
        numerator_symbol,
        "1d",
        limit=daily_limit,
        range_override="10y",
    )
    denominator = await fetch_yahoo_chart_ohlcv(
        denominator_symbol,
        "1d",
        limit=daily_limit,
        range_override="10y",
    )

    if numerator.empty:
        raise ValueError(f"{numerator_symbol} için Yahoo günlük veri boş döndü.")
    if denominator.empty:
        raise ValueError(f"{denominator_symbol} için Yahoo günlük veri boş döndü.")

    # Kur verisini BIST işlem günlerine forward-fill ile hizala.
    denominator_aligned = denominator.reindex(numerator.index, method="ffill")

    joined = numerator.join(denominator_aligned, how="inner", lsuffix="_num", rsuffix="_den")
    joined = joined.dropna(subset=["open_num", "high_num", "low_num", "close_num", "open_den", "high_den", "low_den", "close_den"])

    if joined.empty:
        raise ValueError(f"{numerator_symbol}/{denominator_symbol} için hizalanmış ortak veri boş döndü.")

    ratio_daily = pd.DataFrame(index=joined.index)
    ratio_daily["open"] = joined["open_num"] / joined["open_den"]
    ratio_daily["high"] = joined["high_num"] / joined["high_den"]
    ratio_daily["low"] = joined["low_num"] / joined["low_den"]
    ratio_daily["close"] = joined["close_num"] / joined["close_den"]
    ratio_daily["volume"] = joined["volume_num"].fillna(0)
    ratio_daily = _clean_ohlcv(ratio_daily, limit=0)

    if interval == "1wk":
        return _resample_daily_to_weekly(ratio_daily, limit=limit)

    if interval == "1mo":
        monthly = pd.DataFrame()
        monthly["open"] = ratio_daily["open"].resample("ME").first()
        monthly["high"] = ratio_daily["high"].resample("ME").max()
        monthly["low"] = ratio_daily["low"].resample("ME").min()
        monthly["close"] = ratio_daily["close"].resample("ME").last()
        monthly["volume"] = ratio_daily["volume"].resample("ME").sum()
        return _clean_ohlcv(monthly, limit=limit)

    return _clean_ohlcv(ratio_daily, limit=limit)


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
