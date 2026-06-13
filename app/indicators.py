\
from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)


def atr_sma(df: pd.DataFrame, period: int) -> pd.Series:
    return true_range(df).rolling(period, min_periods=period).mean()


def rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def mfi(df: pd.DataFrame, period: int) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3
    money_flow = typical * df["volume"].fillna(0)
    positive = money_flow.where(typical > typical.shift(1), 0.0)
    negative = money_flow.where(typical < typical.shift(1), 0.0)
    positive_sum = positive.rolling(period, min_periods=period).sum()
    negative_sum = negative.rolling(period, min_periods=period).sum()
    ratio = positive_sum / negative_sum.replace(0, np.nan)
    return (100 - (100 / (1 + ratio))).fillna(50)


def alpha_trend_signal(df: pd.DataFrame, coeff: float = 1.0, period: int = 14, use_rsi_instead_of_mfi: bool = False) -> dict:
    if len(df) < period + 5:
        raise ValueError("AlphaTrend için yeterli veri yok.")

    atr = atr_sma(df, period)
    up_t = df["low"] - atr * coeff
    down_t = df["high"] + atr * coeff
    momentum = rsi(df["close"], period) >= 50 if use_rsi_instead_of_mfi or df["volume"].fillna(0).sum() == 0 else mfi(df, period) >= 50

    alpha = pd.Series(index=df.index, dtype="float64")
    for i in range(len(df)):
        if pd.isna(atr.iloc[i]):
            alpha.iloc[i] = df["close"].iloc[i]
            continue
        prev = alpha.iloc[i - 1] if i > 0 and not pd.isna(alpha.iloc[i - 1]) else df["close"].iloc[i]
        alpha.iloc[i] = max(float(up_t.iloc[i]), float(prev)) if bool(momentum.iloc[i]) else min(float(down_t.iloc[i]), float(prev))

    buy = (alpha > alpha.shift(2)) & (alpha.shift(1) <= alpha.shift(3))
    sell = (alpha < alpha.shift(2)) & (alpha.shift(1) >= alpha.shift(3))
    state = "NEUTRAL"
    last_change_index = None
    for idx in df.index:
        if bool(buy.loc[idx]):
            state = "BUY"
            last_change_index = idx
        elif bool(sell.loc[idx]):
            state = "SELL"
            last_change_index = idx
    return {"indicator": "AlphaTrend", "signal": state, "last_change_time": str(last_change_index) if last_change_index is not None else None, "value": float(alpha.dropna().iloc[-1])}


def supertrend_signal(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> dict:
    if len(df) < period + 5:
        raise ValueError("SuperTrend için yeterli veri yok.")

    atr = atr_sma(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr
    final_upper = pd.Series(index=df.index, dtype="float64")
    final_lower = pd.Series(index=df.index, dtype="float64")
    trend = pd.Series(index=df.index, dtype="object")

    for i in range(len(df)):
        if pd.isna(atr.iloc[i]):
            final_upper.iloc[i] = np.nan
            final_lower.iloc[i] = np.nan
            trend.iloc[i] = "NEUTRAL"
            continue
        if i == 0 or pd.isna(final_upper.iloc[i - 1]):
            final_upper.iloc[i] = basic_upper.iloc[i]
            final_lower.iloc[i] = basic_lower.iloc[i]
            trend.iloc[i] = "BUY" if df["close"].iloc[i] >= hl2.iloc[i] else "SELL"
            continue
        prev_close = df["close"].iloc[i - 1]
        final_upper.iloc[i] = basic_upper.iloc[i] if basic_upper.iloc[i] < final_upper.iloc[i - 1] or prev_close > final_upper.iloc[i - 1] else final_upper.iloc[i - 1]
        final_lower.iloc[i] = basic_lower.iloc[i] if basic_lower.iloc[i] > final_lower.iloc[i - 1] or prev_close < final_lower.iloc[i - 1] else final_lower.iloc[i - 1]
        prev_trend = trend.iloc[i - 1]
        close = df["close"].iloc[i]
        if prev_trend == "SELL" and close > final_upper.iloc[i]:
            trend.iloc[i] = "BUY"
        elif prev_trend == "BUY" and close < final_lower.iloc[i]:
            trend.iloc[i] = "SELL"
        else:
            trend.iloc[i] = prev_trend

    state = str(trend.dropna().iloc[-1])
    last_change_index = None
    previous = None
    for idx, value in trend.dropna().items():
        if value in {"BUY", "SELL"} and previous in {"BUY", "SELL"} and value != previous:
            last_change_index = idx
        if value in {"BUY", "SELL"}:
            previous = value
    st_value = final_lower.iloc[-1] if state == "BUY" else final_upper.iloc[-1]
    return {"indicator": "SuperTrend", "signal": state, "last_change_time": str(last_change_index) if last_change_index is not None else None, "value": float(st_value) if not pd.isna(st_value) else None}


def calculate_all_signals(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        raise ValueError("OHLCV veri seti boş.")
    return [alpha_trend_signal(df), supertrend_signal(df)]
