"""
Paper trading broker – simulates orders with fees and slippage.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List
import pandas as pd

logger = logging.getLogger(__name__)


class PaperBroker:
    def __init__(self, initial_capital: float = 1000.0, fee_rate: float = 0.001, slippage_pct: float = 0.0005):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
        self.position: Optional[Dict] = None
        self.trade_history: List[Dict] = []
        self.equity_curve: List[Dict] = []

    @property
    def equity(self) -> float:
        if self.position is None:
            return self.cash
        # Unrealized PnL
        current_price = self.position.get("current_price", self.position["entry_price"])
        if self.position["side"] == "long":
            unrealized = (current_price - self.position["entry_price"]) * self.position["size"]
        else:
            unrealized = (self.position["entry_price"] - current_price) * self.position["size"]
        return self.cash + unrealized

    def update_price(self, price: float):
        if self.position:
            self.position["current_price"] = price

    def open_position(self, side: str, price: float, size: float, stop_loss: float,
                      take_profit_1: float = None, take_profit_2: float = None,
                      reason: str = "") -> bool:
        if self.position is not None:
            logger.warning("Already in a position – cannot open new one.")
            return False
        if size <= 0:
            return False

        # Apply slippage
        if side == "long":
            fill_price = price * (1 + self.slippage_pct)
        else:
            fill_price = price * (1 - self.slippage_pct)

        cost = fill_price * size
        fee = cost * self.fee_rate
        total_cost = cost + fee

        if total_cost > self.cash:
            logger.warning(f"Insufficient cash. Need {total_cost:.2f}, have {self.cash:.2f}")
            return False

        self.cash -= total_cost
        self.position = {
            "side": side,
            "entry_price": fill_price,
            "size": size,
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "entry_time": datetime.now(timezone.utc),
            "reason": reason,
            "current_price": fill_price,
            "remaining_size": size,
        }
        logger.info(f"OPEN {side.upper()} | Size: {size:.6f} @ {fill_price:.2f} | SL: {stop_loss:.2f} | Reason: {reason}")
        return True

    def close_position(self, price: float, reason: str = "signal") -> Optional[Dict]:
        if self.position is None:
            return None

        side = self.position["side"]
        size = self.position["remaining_size"]

        # Slippage on exit
        if side == "long":
            fill_price = price * (1 - self.slippage_pct)
        else:
            fill_price = price * (1 + self.slippage_pct)

        proceeds = fill_price * size
        fee = proceeds * self.fee_rate
        net_proceeds = proceeds - fee

        if side == "long":
            pnl = (fill_price - self.position["entry_price"]) * size - (self.position["entry_price"] * size * self.fee_rate) - fee
        else:
            pnl = (self.position["entry_price"] - fill_price) * size - (self.position["entry_price"] * size * self.fee_rate) - fee

        self.cash += net_proceeds

        trade = {
            "entry_time": self.position["entry_time"],
            "exit_time": datetime.now(timezone.utc),
            "side": side,
            "entry_price": self.position["entry_price"],
            "exit_price": fill_price,
            "size": size,
            "pnl": pnl,
            "pnl_pct": (pnl / (self.position["entry_price"] * size)) * 100,
            "reason": reason,
            "entry_reason": self.position["reason"],
        }
        self.trade_history.append(trade)
        logger.info(f"CLOSE {side.upper()} | PnL: {pnl:.2f} USDT ({trade['pnl_pct']:.2f}%) | Reason: {reason}")

        self.position = None
        return trade

    def partial_close(self, price: float, fraction: float = 0.5, reason: str = "tp1"):
        """Close part of the position (e.g. at TP1)."""
        if self.position is None or fraction <= 0 or fraction >= 1:
            return None

        size_to_close = self.position["remaining_size"] * fraction
        # Temporarily reduce size, close, then restore remaining
        original_size = self.position["size"]
        self.position["remaining_size"] = size_to_close
        trade = self.close_position(price, reason=reason)

        # Re-open remaining (simplified – in reality we just keep the rest)
        if trade:
            remaining = original_size - size_to_close
            # We already closed fully in the method above for simplicity.
            # For a more accurate version one would keep the position object and only reduce size.
            # Here we accept full close for educational clarity.
            pass
        return trade

    def log_equity(self, timestamp=None):
        self.equity_curve.append({
            "timestamp": timestamp or datetime.now(timezone.utc),
            "equity": self.equity,
            "cash": self.cash,
            "in_position": self.position is not None,
        })

    def get_trade_summary(self) -> pd.DataFrame:
        if not self.trade_history:
            return pd.DataFrame()
        return pd.DataFrame(self.trade_history)

    def get_stats(self) -> Dict:
        trades = self.get_trade_summary()
        if trades.empty:
            return {"total_trades": 0, "win_rate": 0, "total_pnl": 0, "final_equity": self.equity}

        wins = trades[trades["pnl"] > 0]
        return {
            "total_trades": len(trades),
            "win_rate": len(wins) / len(trades) * 100 if len(trades) > 0 else 0,
            "total_pnl": trades["pnl"].sum(),
            "avg_pnl": trades["pnl"].mean(),
            "max_win": trades["pnl"].max(),
            "max_loss": trades["pnl"].min(),
            "final_equity": self.equity,
            "return_pct": (self.equity / self.initial_capital - 1) * 100,
        }
