#!/usr/bin/env python3
"""
============================================================
Crypto Fibonacci + Simplified Elliott Wave Paper Trading Bot
============================================================
EDUCATIONAL PURPOSE ONLY

This bot uses a pragmatic approximation of Fibonacci retracements
and simple swing structure. It is NOT a professional Elliott Wave
system and carries NO guarantee of profitability.

Always start with paper trading.
Never risk money you cannot afford to lose.
============================================================
"""

import yaml
import time
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.data_feed import DataFeed
from src.strategy import FibElliottStrategy
from src.paper_broker import PaperBroker
from src.risk_manager import RiskManager

# Setup logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("main")


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def run_paper_trading(config: dict, duration_days: int = 60, check_interval_minutes: int = 15):
    """
    Run the bot in paper-trading mode for a given number of days.
    In practice you would run this on a VPS / always-on machine.
    """
    logger.info("=" * 60)
    logger.info("STARTING PAPER TRADING MODE")
    logger.info(f"Symbol      : {config['trading']['symbol']}")
    logger.info(f"Timeframe   : {config['trading']['timeframe']}")
    logger.info(f"Capital     : {config['trading']['initial_capital']} USDT")
    logger.info(f"Risk/Trade  : {config['trading']['risk_per_trade']*100}%")
    logger.info(f"Duration    : {duration_days} days (or until stopped)")
    logger.info("=" * 60)

    feed = DataFeed(
        exchange_name=config["exchange"]["name"],
        symbol=config["trading"]["symbol"],
        timeframe=config["trading"]["timeframe"],
    )
    strategy = FibElliottStrategy(config)
    broker = PaperBroker(
        initial_capital=config["trading"]["initial_capital"],
        fee_rate=config["paper_trading"]["fee_rate"],
        slippage_pct=config["paper_trading"]["slippage_pct"],
    )
    risk = RiskManager(
        initial_capital=config["trading"]["initial_capital"],
        risk_per_trade=config["trading"]["risk_per_trade"],
        max_drawdown_pct=config["trading"]["max_drawdown_pct"],
    )

    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(days=duration_days)
    iteration = 0

    logger.info("Bot is running. Press Ctrl+C to stop early.")
    logger.info("Fetching initial data...")

    try:
        while datetime.now(timezone.utc) < end_time:
            iteration += 1
            try:
                # Fetch enough candles for indicators
                df = feed.fetch_ohlcv(limit=300)
                current_price = df["close"].iloc[-1]
                broker.update_price(current_price)
                risk.update_equity(broker.equity)

                # Check existing position for SL / TP
                if broker.position and risk.can_trade():
                    action = risk.check_stop_or_tp(broker.position, current_price)
                    if action:
                        broker.close_position(current_price, reason=action)

                # Look for new signal only if flat and risk allows
                if broker.position is None and risk.can_trade():
                    signal = strategy.generate_signal(df)
                    if signal:
                        size = risk.calculate_position_size(
                            equity=broker.equity,
                            entry_price=signal["entry"],
                            stop_price=signal["stop_loss"],
                        )
                        if size > 0:
                            broker.open_position(
                                side=signal["side"],
                                price=signal["entry"],
                                size=size,
                                stop_loss=signal["stop_loss"],
                                take_profit_1=signal["take_profit_1"],
                                take_profit_2=signal["take_profit_2"],
                                reason=signal["reason"],
                            )

                # Log equity every iteration
                broker.log_equity()

                # Periodic status
                if iteration % 4 == 0:  # roughly every hour if interval=15min
                    stats = broker.get_stats()
                    logger.info(
                        f"Equity: {broker.equity:.2f} USDT | "
                        f"Trades: {stats['total_trades']} | "
                        f"WinRate: {stats.get('win_rate', 0):.1f}% | "
                        f"Return: {stats.get('return_pct', 0):.2f}%"
                    )

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)

            # Sleep until next check
            time.sleep(check_interval_minutes * 60)

    except KeyboardInterrupt:
        logger.info("Stopped by user.")

    # Final report
    logger.info("=" * 60)
    logger.info("PAPER TRADING FINISHED / STOPPED")
    stats = broker.get_stats()
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 60)

    # Save trade log
    trades_df = broker.get_trade_summary()
    if not trades_df.empty:
        trades_df.to_csv(config["logging"]["trade_log"], index=False)
        logger.info(f"Trades saved to {config['logging']['trade_log']}")

    equity_df = pd.DataFrame(broker.equity_curve)
    if not equity_df.empty:
        equity_df.to_csv(config["logging"]["equity_log"], index=False)
        logger.info(f"Equity curve saved to {config['logging']['equity_log']}")

    return broker


def run_quick_backtest(config: dict, lookback_candles: int = 500):
    """
    Simple sequential backtest on recent history (for quick validation).
    Not a full event-driven backtester, but useful to see behaviour.
    """
    import pandas as pd

    logger.info("Running quick historical simulation...")
    feed = DataFeed(
        exchange_name=config["exchange"]["name"],
        symbol=config["trading"]["symbol"],
        timeframe=config["trading"]["timeframe"],
    )
    strategy = FibElliottStrategy(config)
    broker = PaperBroker(
        initial_capital=config["trading"]["initial_capital"],
        fee_rate=config["paper_trading"]["fee_rate"],
        slippage_pct=config["paper_trading"]["slippage_pct"],
    )
    risk = RiskManager(
        initial_capital=config["trading"]["initial_capital"],
        risk_per_trade=config["trading"]["risk_per_trade"],
        max_drawdown_pct=config["trading"]["max_drawdown_pct"],
    )

    df = feed.fetch_ohlcv(limit=lookback_candles)
    df = strategy.prepare_data(df)

    # Walk forward candle by candle
    for i in range(250, len(df)):  # need enough history for EMAs
        window = df.iloc[: i + 1]
        current_price = window["close"].iloc[-1]
        broker.update_price(current_price)
        risk.update_equity(broker.equity)

        if broker.position:
            action = risk.check_stop_or_tp(broker.position, current_price)
            if action:
                broker.close_position(current_price, reason=action)

        if broker.position is None and risk.can_trade():
            signal = strategy.generate_signal(window)
            if signal:
                size = risk.calculate_position_size(
                    equity=broker.equity,
                    entry_price=signal["entry"],
                    stop_price=signal["stop_loss"],
                )
                if size > 0:
                    broker.open_position(
                        side=signal["side"],
                        price=signal["entry"],
                        size=size,
                        stop_loss=signal["stop_loss"],
                        take_profit_1=signal["take_profit_1"],
                        take_profit_2=signal["take_profit_2"],
                        reason=signal["reason"],
                    )

        broker.log_equity(timestamp=window.index[-1])

    # Close any open position at the end
    if broker.position:
        broker.close_position(df["close"].iloc[-1], reason="end_of_backtest")

    stats = broker.get_stats()
    logger.info("=" * 60)
    logger.info("QUICK BACKTEST RESULTS")
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 60)

    trades_df = broker.get_trade_summary()
    if not trades_df.empty:
        print("\nLast trades:")
        print(trades_df.tail(10).to_string())
        trades_df.to_csv("logs/backtest_trades.csv", index=False)

    return broker


def run_once(config: dict):
    """
    Single-run mode for GitHub Actions.
    Loads previous state, checks market once, updates position if needed, saves state.
    """
    from src.state import load_state, save_state, append_trade, append_equity
    from datetime import datetime, timezone

    logger.info("=" * 60)
    logger.info("SINGLE RUN (GitHub Actions mode)")
    logger.info("=" * 60)

    initial_capital = config["trading"]["initial_capital"]
    state = load_state(initial_capital)

    feed = DataFeed(
        exchange_name=config["exchange"]["name"],
        symbol=config["trading"]["symbol"],
        timeframe=config["trading"]["timeframe"],
    )
    strategy = FibElliottStrategy(config)
    risk = RiskManager(
        initial_capital=initial_capital,
        risk_per_trade=config["trading"]["risk_per_trade"],
        max_drawdown_pct=config["trading"]["max_drawdown_pct"],
    )

    # Restore risk manager peak / halt status
    risk.peak_equity = state.get("peak_equity", initial_capital)
    risk.trading_halted = state.get("trading_halted", False)

    # Build a temporary broker-like object from state
    class StateBroker:
        def __init__(self, state):
            self.cash = state["cash"]
            self.position = state.get("position")
            self.initial_capital = state.get("initial_capital", initial_capital)
            self.fee_rate = config["paper_trading"]["fee_rate"]
            self.slippage_pct = config["paper_trading"]["slippage_pct"]
            self.trade_history = state.get("trade_history", [])

        @property
        def equity(self):
            if self.position is None:
                return self.cash
            # cash already has margin deducted, so we add margin back + unrealized PnL
            price = self.position.get("current_price", self.position["entry_price"])
            entry = self.position["entry_price"]
            size = self.position["size"]
            margin = self.position.get("margin_used", entry * size)
            if self.position["side"] == "long":
                unrealized = (price - entry) * size
            else:
                unrealized = (entry - price) * size
            return self.cash + margin + unrealized

        def update_price(self, price):
            if self.position:
                self.position["current_price"] = price

        def open_position(self, side, price, size, stop_loss, take_profit_1=None, take_profit_2=None, reason=""):
            if self.position is not None or size <= 0:
                return False
            if side == "long":
                fill = price * (1 + self.slippage_pct)
            else:
                fill = price * (1 - self.slippage_pct)
            cost = fill * size
            fee = cost * self.fee_rate
            if cost + fee > self.cash:
                return False
            self.cash -= (cost + fee)
            self.position = {
                "side": side,
                "entry_price": fill,
                "size": size,
                "stop_loss": stop_loss,
                "take_profit_1": take_profit_1,
                "take_profit_2": take_profit_2,
                "entry_time": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "current_price": fill,
                "remaining_size": size,
            }
            logger.info(f"OPEN {side.upper()} | {size:.6f} @ {fill:.2f} | SL: {stop_loss:.2f}")
            return True

        def close_position(self, price, reason="signal"):
            if self.position is None:
                return None
            side = self.position["side"]
            size = self.position["remaining_size"]
            entry = self.position["entry_price"]
            margin = self.position.get("margin_used", entry * size)

            if side == "long":
                fill = price * (1 - self.slippage_pct)
                pnl = (fill - entry) * size
            else:
                fill = price * (1 + self.slippage_pct)
                pnl = (entry - fill) * size

            exit_fee = (fill * size) * self.fee_rate
            # Release margin + PnL - exit fee
            self.cash += margin + pnl - exit_fee

            trade = {
                "entry_time": self.position["entry_time"],
                "exit_time": datetime.now(timezone.utc).isoformat(),
                "side": side,
                "entry_price": entry,
                "exit_price": fill,
                "size": size,
                "pnl": round(pnl - (entry * size * self.fee_rate) - exit_fee, 4),
                "pnl_pct": round(((pnl - (entry * size * self.fee_rate) - exit_fee) / (entry * size)) * 100, 3),
                "reason": reason,
                "entry_reason": self.position.get("reason", ""),
            }
            self.trade_history.append(trade)
            append_trade(trade)
            logger.info(f"CLOSE {side.upper()} | PnL: {trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%) | {reason}")
            self.position = None
            return trade

    broker = StateBroker(state)

    try:
        df = feed.fetch_ohlcv(limit=300)
        current_price = float(df["close"].iloc[-1])
        broker.update_price(current_price)
        risk.update_equity(broker.equity)

        # Check SL / TP
        if broker.position and risk.can_trade():
            action = risk.check_stop_or_tp(broker.position, current_price)
            if action:
                broker.close_position(current_price, reason=action)

        # New signal?
        if broker.position is None and risk.can_trade():
            signal = strategy.generate_signal(df)
            if signal:
                size = risk.calculate_position_size(
                    equity=broker.equity,
                    entry_price=signal["entry"],
                    stop_price=signal["stop_loss"],
                )
                if size > 0:
                    broker.open_position(
                        side=signal["side"],
                        price=signal["entry"],
                        size=size,
                        stop_loss=signal["stop_loss"],
                        take_profit_1=signal["take_profit_1"],
                        take_profit_2=signal["take_profit_2"],
                        reason=signal["reason"],
                    )

        # Persist
        new_state = {
            "cash": broker.cash,
            "initial_capital": initial_capital,
            "position": broker.position,
            "peak_equity": risk.peak_equity,
            "trading_halted": risk.trading_halted,
            "trade_history": broker.trade_history,
        }
        save_state(new_state)
        append_equity(broker.equity, broker.cash, broker.position is not None)

        logger.info(f"Current equity: {broker.equity:.2f} USDT | Cash: {broker.cash:.2f} | "
                    f"Position: {'YES' if broker.position else 'NO'}")
        if broker.position:
            logger.info(f"  Side: {broker.position['side']} | Entry: {broker.position['entry_price']:.2f} | "
                        f"Size: {broker.position['size']:.6f}")

    except Exception as e:
        logger.error(f"Error in single run: {e}", exc_info=True)
        raise

    logger.info("Single run finished.")
    return broker


if __name__ == "__main__":
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser(description="Fib + Elliott Paper Trading Bot")
    parser.add_argument("--mode", choices=["paper", "backtest", "once"], default="backtest",
                        help="paper = continuous loop | backtest = historical | once = single check (GitHub Actions)")
    parser.add_argument("--days", type=int, default=60, help="Duration for paper mode (days)")
    parser.add_argument("--interval", type=int, default=15, help="Check interval in minutes (paper mode)")
    args = parser.parse_args()

    config = load_config()

    if args.mode == "backtest":
        run_quick_backtest(config)
    elif args.mode == "once":
        run_once(config)
    else:
        run_paper_trading(config, duration_days=args.days, check_interval_minutes=args.interval)
