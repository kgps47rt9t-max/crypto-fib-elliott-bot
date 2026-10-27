"""
Indicators: Fibonacci retracements + simplified swing / wave structure detection.
This is a pragmatic approximation, NOT professional Elliott Wave counting.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


def find_pivots(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """
    Simple pivot high / pivot low detection.
    A pivot high is a high that is higher than `lookback` bars on both sides.
    """
    df = df.copy()
    df["pivot_high"] = np.nan
    df["pivot_low"] = np.nan

    highs = df["high"].values
    lows = df["low"].values

    for i in range(lookback, len(df) - lookback):
        if highs[i] == max(highs[i - lookback : i + lookback + 1]):
            df.iloc[i, df.columns.get_loc("pivot_high")] = highs[i]
        if lows[i] == min(lows[i - lookback : i + lookback + 1]):
            df.iloc[i, df.columns.get_loc("pivot_low")] = lows[i]

    return df


def get_last_significant_swing(df: pd.DataFrame, min_swing_pct: float = 3.0) -> Optional[Dict]:
    """
    Find the most recent significant swing (impulse candidate).
    Returns dict with type ('up' or 'down'), start_price, end_price, start_idx, end_idx.
    """
    pivots = df.dropna(subset=["pivot_high", "pivot_low"], how="all")
    if len(pivots) < 2:
        return None

    # Walk backwards to find last meaningful move
    last_high_idx = df["pivot_high"].last_valid_index()
    last_low_idx = df["pivot_low"].last_valid_index()

    if last_high_idx is None or last_low_idx is None:
        return None

    # Determine direction of the last impulse
    if last_high_idx > last_low_idx:
        # Last pivot was a high → potential up-impulse from previous low
        start_idx = last_low_idx
        end_idx = last_high_idx
        start_price = df.loc[start_idx, "low"]
        end_price = df.loc[end_idx, "high"]
        direction = "up"
    else:
        # Last pivot was a low → potential down-impulse from previous high
        start_idx = last_high_idx
        end_idx = last_low_idx
        start_price = df.loc[start_idx, "high"]
        end_price = df.loc[end_idx, "low"]
        direction = "down"

    move_pct = abs(end_price - start_price) / start_price * 100
    if move_pct < min_swing_pct:
        return None

    return {
        "direction": direction,
        "start_price": float(start_price),
        "end_price": float(end_price),
        "start_idx": start_idx,
        "end_idx": end_idx,
        "move_pct": move_pct,
    }


def calculate_fib_levels(start: float, end: float, direction: str) -> Dict[str, float]:
    """
    Calculate classic Fibonacci retracement and extension levels.
    """
    diff = abs(end - start)
    levels = {}

    if direction == "up":
        # Retracement from high back down
        levels["0.0"] = end
        levels["0.236"] = end - 0.236 * diff
        levels["0.382"] = end - 0.382 * diff
        levels["0.5"] = end - 0.5 * diff
        levels["0.618"] = end - 0.618 * diff
        levels["0.786"] = end - 0.786 * diff
        levels["1.0"] = start
        # Extensions above the high
        levels["1.272"] = end + 0.272 * diff
        levels["1.618"] = end + 0.618 * diff
    else:
        # Retracement from low back up
        levels["0.0"] = end
        levels["0.236"] = end + 0.236 * diff
        levels["0.382"] = end + 0.382 * diff
        levels["0.5"] = end + 0.5 * diff
        levels["0.618"] = end + 0.618 * diff
        levels["0.786"] = end + 0.786 * diff
        levels["1.0"] = start
        # Extensions below the low
        levels["1.272"] = end - 0.272 * diff
        levels["1.618"] = end - 0.618 * diff

    return levels


def add_emas(df: pd.DataFrame, fast: int = 50, slow: int = 200) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=fast, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=slow, adjust=False).mean()
    return df


def get_trend(df: pd.DataFrame) -> str:
    """Simple trend filter using EMAs."""
    if len(df) < 200:
        return "neutral"
    last = df.iloc[-1]
    if last["ema_fast"] > last["ema_slow"] and last["close"] > last["ema_fast"]:
        return "up"
    elif last["ema_fast"] < last["ema_slow"] and last["close"] < last["ema_fast"]:
        return "down"
    return "neutral"
