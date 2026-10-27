"""
Risk management: position sizing, stop-loss, max drawdown protection.
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, initial_capital: float, risk_per_trade: float = 0.02, max_drawdown_pct: float = 0.15):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_drawdown_pct = max_drawdown_pct
        self.peak_equity = initial_capital
        self.trading_halted = False

    def update_equity(self, current_equity: float):
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        if drawdown >= self.max_drawdown_pct:
            self.trading_halted = True
            logger.warning(f"MAX DRAWDOWN reached ({drawdown*100:.1f}%). Trading halted.")

    def can_trade(self) -> bool:
        return not self.trading_halted

    def calculate_position_size(self, equity: float, entry_price: float, stop_price: float) -> float:
        """
        Returns position size in base currency (e.g. BTC amount).
        Risk is fixed percentage of current equity.
        """
        if entry_price <= 0 or stop_price <= 0:
            return 0.0

        risk_amount = equity * self.risk_per_trade
        price_diff = abs(entry_price - stop_price)

        if price_diff == 0:
            return 0.0

        size = risk_amount / price_diff
        # Safety: never risk more than available equity
        max_size = (equity * 0.95) / entry_price
        size = min(size, max_size)
        return round(size, 6)

    def check_stop_or_tp(self, position: Dict, current_price: float) -> Optional[str]:
        """
        Returns 'stop', 'tp1', 'tp2' or None.
        """
        side = position["side"]
        stop = position["stop_loss"]
        tp1 = position.get("take_profit_1")
        tp2 = position.get("take_profit_2")

        if side == "long":
            if current_price <= stop:
                return "stop"
            if tp2 and current_price >= tp2:
                return "tp2"
            if tp1 and current_price >= tp1:
                return "tp1"
        else:  # short
            if current_price >= stop:
                return "stop"
            if tp2 and current_price <= tp2:
                return "tp2"
            if tp1 and current_price <= tp1:
                return "tp1"
        return None
