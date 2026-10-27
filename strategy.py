"""
Conservative Fibonacci + simplified swing strategy.
"""

import logging
from typing import Optional, Dict
import pandas as pd
from .indicators import find_pivots, get_last_significant_swing, calculate_fib_levels, add_emas, get_trend

logger = logging.getLogger(__name__)


class FibElliottStrategy:
    def __init__(self, config: dict):
        self.cfg = config["strategy"]
        self.fib_entry_low = self.cfg["fib_entry_low"]
        self.fib_entry_high = self.cfg["fib_entry_high"]
        self.fib_stop_buffer = self.cfg["fib_stop_buffer"]
        self.fib_tp1 = self.cfg["fib_tp1"]
        self.fib_tp2 = self.cfg["fib_tp2"]
        self.min_swing_pct = self.cfg["min_swing_pct"]
        self.pivot_lookback = self.cfg["pivot_lookback"]
        self.require_trend = self.cfg["require_trend_alignment"]
        self.ema_fast = self.cfg["ema_fast"]
        self.ema_slow = self.cfg["ema_slow"]

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = find_pivots(df, lookback=self.pivot_lookback)
        df = add_emas(df, fast=self.ema_fast, slow=self.ema_slow)
        return df

    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Returns a signal dict or None.
        Signal format:
        {
            "side": "long" | "short",
            "entry": float,
            "stop_loss": float,
            "take_profit_1": float,
            "take_profit_2": float,
            "reason": str
        }
        """
        if len(df) < self.ema_slow + 10:
            return None

        df = self.prepare_data(df)
        swing = get_last_significant_swing(df, min_swing_pct=self.min_swing_pct)
        if swing is None:
            return None

        trend = get_trend(df)
        current_price = df["close"].iloc[-1]
        levels = calculate_fib_levels(swing["start_price"], swing["end_price"], swing["direction"])

        # Conservative: only trade in direction of the last impulse AND trend filter
        if swing["direction"] == "up" and (not self.require_trend or trend == "up"):
            # Look for long on retracement into 50-61.8% zone
            zone_low = levels["0.618"]
            zone_high = levels["0.5"]
            if zone_low <= current_price <= zone_high:
                stop = swing["start_price"] * (1 - self.fib_stop_buffer)
                # Ensure stop is below entry
                stop = min(stop, current_price * 0.97)
                tp1 = levels["1.272"]
                tp2 = levels["1.618"]
                return {
                    "side": "long",
                    "entry": current_price,
                    "stop_loss": stop,
                    "take_profit_1": tp1,
                    "take_profit_2": tp2,
                    "reason": f"Bullish swing retracement into 50-61.8% Fib | Swing {swing['move_pct']:.1f}%",
                }

        elif swing["direction"] == "down" and (not self.require_trend or trend == "down"):
            # Look for short on retracement into 50-61.8% zone
            zone_low = levels["0.5"]
            zone_high = levels["0.618"]
            if zone_low <= current_price <= zone_high:
                stop = swing["start_price"] * (1 + self.fib_stop_buffer)
                stop = max(stop, current_price * 1.03)
                tp1 = levels["1.272"]
                tp2 = levels["1.618"]
                return {
                    "side": "short",
                    "entry": current_price,
                    "stop_loss": stop,
                    "take_profit_1": tp1,
                    "take_profit_2": tp2,
                    "reason": f"Bearish swing retracement into 50-61.8% Fib | Swing {swing['move_pct']:.1f}%",
                }

        return None
