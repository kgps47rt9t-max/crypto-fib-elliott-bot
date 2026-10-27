"""
Data feed module using CCXT.
Fetches OHLCV data for the configured symbol and timeframe.
"""

import ccxt
import pandas as pd
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DataFeed:
    def __init__(self, exchange_name: str = "binance", symbol: str = "BTC/USDT", timeframe: str = "4h"):
        self.symbol = symbol
        self.timeframe = timeframe
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        logger.info(f"DataFeed initialized: {exchange_name} | {symbol} | {timeframe}")

    def fetch_ohlcv(self, limit: int = 500, since: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch OHLCV candles and return as DataFrame.
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=limit, since=since)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            df = df.astype(float)
            logger.debug(f"Fetched {len(df)} candles. Last close: {df['close'].iloc[-1]:.2f}")
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV: {e}")
            raise

    def fetch_latest_price(self) -> float:
        ticker = self.exchange.fetch_ticker(self.symbol)
        return float(ticker["last"])
