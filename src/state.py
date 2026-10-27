"""
Simple state persistence for paper trading across GitHub Actions runs.
Saves/loads position, cash, trade history and equity to JSON + CSV.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List
import pandas as pd

logger = logging.getLogger(__name__)

STATE_FILE = Path("logs/state.json")
TRADES_FILE = Path("logs/trades.csv")
EQUITY_FILE = Path("logs/equity.csv")


def load_state(initial_capital: float = 1000.0) -> Dict:
    """Load previous state or return fresh state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            logger.info(f"State loaded. Cash: {state.get('cash', initial_capital):.2f} | "
                        f"In position: {state.get('position') is not None}")
            return state
        except Exception as e:
            logger.warning(f"Could not load state: {e}. Starting fresh.")

    return {
        "cash": initial_capital,
        "initial_capital": initial_capital,
        "position": None,
        "peak_equity": initial_capital,
        "trading_halted": False,
        "trade_history": [],
        "last_run": None,
    }


def save_state(state: Dict):
    """Save current state to disk."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)
    logger.info(f"State saved. Cash: {state['cash']:.2f}")


def append_trade(trade: Dict):
    """Append a closed trade to the CSV log."""
    TRADES_FILE.parent.mkdir(exist_ok=True)
    df = pd.DataFrame([trade])
    header = not TRADES_FILE.exists()
    df.to_csv(TRADES_FILE, mode="a", header=header, index=False)


def append_equity(equity: float, cash: float, in_position: bool):
    """Append equity snapshot."""
    EQUITY_FILE.parent.mkdir(exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "equity": equity,
        "cash": cash,
        "in_position": in_position,
    }
    df = pd.DataFrame([row])
    header = not EQUITY_FILE.exists()
    df.to_csv(EQUITY_FILE, mode="a", header=header, index=False)
