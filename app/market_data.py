\
from __future__ import annotations

import httpx
import pandas as pd
import yfinance as yf

BINANCE_BASE_URL = "https://api.binance.com/api/v3/klines"


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            df[col] = 0.0
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df = df.dropna(subset=["open", "high", "low", "close"])
    df.index = pd.to_datetime(df.index)
    return df


async def fetch_binance_klines(symbol: str, interval: str, limit: int = 350) -> pd.DataFrame:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(BINANCE_BASE_URL, params={"symbol": symbol, "interval": interval, "limit": limit})
        response.raise_for_status()
        rows = response.json()

    df = pd.DataFrame(rows, columns=[
        "open_time","open","high","low","close","volume","close_time","quote_asset_volume",
        "number_of_trades","taker_buy_base_asset_volume","taker_buy_quote_asset_volume","ignore"
    ])
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["datetime"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df.set_index("datetime")[["open","high","low","close","volume"]].dropna()


def fetch_yfinance_ohlcv(symbol: str, interval: str, limit: int = 350) -> pd.DataFrame:
    period = "10y" if interval in {"1wk", "1mo"} else "2y"
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    df = _normalize_ohlcv(df)
    return df.tail(limit) if limit and len(df) > limit else df


def fetch_yfinance_ratio_ohlcv(numerator_symbol: str, denominator_symbol: str, interval: str, limit: int = 350) -> pd.DataFrame:
    num = fetch_yfinance_ohlcv(numerator_symbol, interval, limit=limit)
    den = fetch_yfinance_ohlcv(denominator_symbol, interval, limit=limit)
    if num.empty or den.empty:
        return pd.DataFrame(columns=["open","high","low","close","volume"])
    joined = num.join(den, how="inner", lsuffix="_num", rsuffix="_den")
    if joined.empty:
        return pd.DataFrame(columns=["open","high","low","close","volume"])
    out = pd.DataFrame(index=joined.index)
    out["open"] = joined["open_num"] / joined["open_den"]
    out["high"] = joined["high_num"] / joined["high_den"]
    out["low"] = joined["low_num"] / joined["low_den"]
    out["close"] = joined["close_num"] / joined["close_den"]
    out["volume"] = joined["volume_num"]
    out = out.dropna(subset=["open","high","low","close"])
    return out.tail(limit) if limit and len(out) > limit else out


async def fetch_ohlcv_for_instrument(instrument: dict, limit: int = 350) -> pd.DataFrame:
    provider = instrument.get("data_provider")
    interval = instrument.get("engine_interval") or ("1wk" if instrument.get("timeframe") == "1W" else "1d")
    if provider == "binance":
        return await fetch_binance_klines(instrument["data_symbol"], interval, limit=limit)
    if provider == "yfinance":
        return fetch_yfinance_ohlcv(instrument["data_symbol"], interval, limit=limit)
    if provider == "yfinance_ratio":
        return fetch_yfinance_ratio_ohlcv(instrument["numerator_symbol"], instrument["denominator_symbol"], interval, limit=limit)
    raise ValueError(f"Desteklenmeyen data_provider: {provider}")
