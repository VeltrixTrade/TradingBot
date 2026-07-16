"""
Mustafa Bot - Price Fetcher Engine (TradingView OANDA Edition)
يجلب الأسعار اللحظية وبيانات الشموع التاريخية مباشرة من TradingView (OANDA)
"""

import logging
import urllib.request
import json
import time
from typing import Optional, Dict
import pandas as pd

from config import Config

logger = logging.getLogger('mustafa_bot.data.price_fetcher')

# Shared global instance of tvDatafeed to reuse websocket connection
_tv_client = None

def get_tv_client():
    global _tv_client
    if _tv_client is None:
        try:
            from tvDatafeed import TvDatafeed
            # Initialize with no login (completely free public access)
            _tv_client = TvDatafeed()
            logger.info("⚡ Shared TradingView tvDatafeed client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize TradingView tvDatafeed client: {e}")
    return _tv_client


# Map symbol keys to TradingView (ticker, exchange)
TRADINGVIEW_SYMBOLS = {
    'XAU/USD': ('XAUUSD', 'OANDA'),
    'EUR/USD': ('EURUSD', 'OANDA'),
    'GBP/USD': ('GBPUSD', 'OANDA'),
    'USD/JPY': ('USDJPY', 'OANDA'),
    'NAS100': ('NDX', 'NASDAQ'),       # Nasdaq Index
    'US30': ('US30USD', 'OANDA'),       # Dow Jones Index CFD
    'BTC/USD': ('BTCUSDT', 'BINANCE'),  # Bitcoin Spot
    'ETH/USD': ('ETHUSDT', 'BINANCE')   # Ethereum Spot
}

# Map symbol keys to TwelveData symbols (preserved for compatibility/metadata reference)
TWELVEDATA_SYMBOL_MAP = {
    'XAU/USD': 'XAU/USD',
    'EUR/USD': 'EUR/USD',
    'GBP/USD': 'GBP/USD',
    'USD/JPY': 'USD/JPY',
    'NAS100': 'NDX',
    'US30': 'DJI',
    'BTC/USD': 'BTC/USD',
    'ETH/USD': 'ETH/USD',
}

# Map standard timeframes to tvDatafeed Intervals
from tvDatafeed import Interval
TIMEFRAME_MAP = {
    '1m': Interval.in_1_minute,
    '3m': Interval.in_3_minute,
    '5m': Interval.in_5_minute,
    '15m': Interval.in_15_minute,
    '30m': Interval.in_30_minute,
    '1h': Interval.in_1_hour,
    '2h': Interval.in_2_hour,
    '4h': Interval.in_4_hour,
    '1d': Interval.in_daily,
    '1w': Interval.in_weekly,
    '1mo': Interval.in_monthly,
    
    # MT5 syntax compatibility
    'm1': Interval.in_1_minute,
    'm5': Interval.in_5_minute,
    'm15': Interval.in_15_minute,
    'm30': Interval.in_30_minute,
    'h1': Interval.in_1_hour,
    'h4': Interval.in_4_hour,
    'd1': Interval.in_daily,
    'w1': Interval.in_weekly,
    'mn1': Interval.in_monthly
}


class PriceFetcher:
    """Synchronous market data engine fetching real-time and historical candles directly from TradingView OANDA."""

    def __init__(self, symbol_key: str):
        self.symbol_key = symbol_key  # e.g., 'XAU/USD'
        self._price_source = 'UNKNOWN'

    def get_current_price(self) -> Optional[float]:
        """Fetch real-time close price directly from TradingView (OANDA) with retries."""
        client = get_tv_client()
        if not client:
            logger.error("tvDatafeed client not available.")
            return None

        tv_info = TRADINGVIEW_SYMBOLS.get(self.symbol_key)
        if not tv_info:
            logger.error(f"Symbol {self.symbol_key} is not mapped in TRADINGVIEW_SYMBOLS")
            return None

        symbol, exchange = tv_info
        for attempt in range(3):
            try:
                # Fetch last 1-minute bar to get the absolute latest close price
                df = client.get_hist(symbol=symbol, exchange=exchange, interval=Interval.in_1_minute, n_bars=1)
                if df is not None and not df.empty and 'close' in df.columns:
                    price = float(df['close'].iloc[-1])
                    self._price_source = f'TRADINGVIEW_{exchange}'
                    return price
            except Exception as e:
                logger.warning(f"⚠️ TradingView price fetch attempt {attempt+1} failed for {self.symbol_key}: {e}")
                time.sleep(1.0)
        return None

    def get_historical_data(self, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Fetch historical candles from TradingView (OANDA) with retries."""
        client = get_tv_client()
        if not client:
            logger.error("tvDatafeed client not available.")
            return None

        tv_info = TRADINGVIEW_SYMBOLS.get(self.symbol_key)
        if not tv_info:
            logger.error(f"Symbol {self.symbol_key} is not mapped in TRADINGVIEW_SYMBOLS")
            return None

        symbol, exchange = tv_info
        tv_interval = TIMEFRAME_MAP.get(timeframe.lower())
        if not tv_interval:
            logger.warning(f"Unsupported timeframe: {timeframe}")
            return None

        for attempt in range(3):
            try:
                df = client.get_hist(symbol=symbol, exchange=exchange, interval=tv_interval, n_bars=n_bars)
                if df is not None and not df.empty:
                    df = df.copy()
                    df.index.name = 'time'
                    
                    # Format to match the engine expectations: open, high, low, close, tick_volume
                    if 'volume' in df.columns:
                        df.rename(columns={'volume': 'tick_volume'}, inplace=True)
                    else:
                        df['tick_volume'] = 0.0

                    # Ensure all numeric columns are float
                    for col in ['open', 'high', 'low', 'close', 'tick_volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    cols = ['open', 'high', 'low', 'close', 'tick_volume']
                    logger.info(f"Fetched {len(df)} candles for {self.symbol_key} ({timeframe}) via TradingView {exchange}")
                    return df[cols].dropna()
            except Exception as e:
                logger.warning(f"⚠️ TradingView candles fetch attempt {attempt+1} failed for {self.symbol_key} ({timeframe}): {e}")
                time.sleep(1.0)
        return None

    def get_multi_timeframe_data(self, timeframes: list = None) -> Dict[str, pd.DataFrame]:
        """Fetch candles for multiple timeframes."""
        if timeframes is None:
            timeframes = ['1d', '4h', '1h', '30m', '15m', '5m']

        mtf_data = {}
        for tf in timeframes:
            df = self.get_historical_data(tf, n_bars=400)
            if df is not None and not df.empty:
                mtf_data[tf] = df
        return mtf_data
