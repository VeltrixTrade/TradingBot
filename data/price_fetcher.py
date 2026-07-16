"""
Mustafa Bot - Price Fetcher Engine (TradingView OANDA Edition)
يجلب الأسعار اللحظية وبيانات الشموع التاريخية مباشرة من TradingView (OANDA) مع التخزين المؤقت في الذاكرة
"""

import logging
import urllib.request
import json
import time
import asyncio
from typing import Optional, Dict
import pandas as pd

from config import Config

logger = logging.getLogger('mustafa_bot.data.price_fetcher')

# Shared global instance of tvDatafeed to reuse websocket connection
_tv_client = None

# Shared global candles memory cache
_candles_cache = {}

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
    """High-performance market data engine with asynchronous background candle caching."""

    def __init__(self, symbol_key: str):
        self.symbol_key = symbol_key  # e.g., 'XAU/USD'
        self._price_source = 'UNKNOWN'

    def get_current_price(self, chat_id: Optional[int] = None) -> Optional[float]:
        """Fetch real-time close price returning from memory cache first for <1ms response."""
        global _candles_cache
        if self.symbol_key in _candles_cache:
            for tf in ['15m', '5m', '1m', '30m', '1h']:
                if tf in _candles_cache[self.symbol_key]:
                    df = _candles_cache[self.symbol_key][tf]
                    if df is not None and not df.empty and 'close' in df.columns:
                        return float(df['close'].iloc[-1])

        # Fallback to TradingView get_hist n_bars=1
        client = get_tv_client()
        if not client:
            return None
        tv_info = TRADINGVIEW_SYMBOLS.get(self.symbol_key)
        if not tv_info:
            return None
        symbol, exchange = tv_info
        for attempt in range(3):
            try:
                df = client.get_hist(symbol=symbol, exchange=exchange, interval=Interval.in_1_minute, n_bars=1)
                if df is not None and not df.empty and 'close' in df.columns:
                    return float(df['close'].iloc[-1])
            except Exception as e:
                logger.warning(f"Fallback current price fetch failed for {self.symbol_key}: {e}")
                time.sleep(0.1)
        return None

    async def fetch_historical_data_async(self, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Asynchronously fetch historical candles using memory cache and lightweight delta updates."""
        global _candles_cache
        if self.symbol_key not in _candles_cache:
            _candles_cache[self.symbol_key] = {}

        cached_df = _candles_cache[self.symbol_key].get(timeframe)
        client = get_tv_client()
        if not client:
            return cached_df

        tv_info = TRADINGVIEW_SYMBOLS.get(self.symbol_key)
        if not tv_info:
            return cached_df

        symbol, exchange = tv_info
        tv_interval = TIMEFRAME_MAP.get(timeframe.lower())
        if not tv_interval:
            return cached_df

        # Optimization: if cache exists, fetch only the last 3 candles to update/append delta
        fetch_bars = 3 if cached_df is not None and not cached_df.empty else n_bars

        for attempt in range(3):
            try:
                # Offload blocking WebSocket/network call to a separate worker thread
                df = await asyncio.to_thread(client.get_hist, symbol=symbol, exchange=exchange, interval=tv_interval, n_bars=fetch_bars)
                if df is not None and not df.empty:
                    df = df.copy()
                    df.index.name = 'time'
                    if 'volume' in df.columns:
                        df.rename(columns={'volume': 'tick_volume'}, inplace=True)
                    else:
                        df['tick_volume'] = 0.0

                    for col in ['open', 'high', 'low', 'close', 'tick_volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                    new_df = df[['open', 'high', 'low', 'close', 'tick_volume']].dropna()

                    if cached_df is not None and not cached_df.empty:
                        merged = pd.concat([cached_df, new_df])
                        merged = merged[~merged.index.duplicated(keep='last')]
                        merged.sort_index(inplace=True)
                        if len(merged) > n_bars:
                            merged = merged.tail(n_bars)
                        _candles_cache[self.symbol_key][timeframe] = merged
                    else:
                        _candles_cache[self.symbol_key][timeframe] = new_df

                    return _candles_cache[self.symbol_key][timeframe]
            except Exception as e:
                logger.warning(f"Async TV fetch attempt {attempt+1} failed for {self.symbol_key} ({timeframe}): {e}")
                await asyncio.sleep(0.1)

        return cached_df

    async def fetch_multi_timeframe_data_async(self, timeframes: list = None) -> Dict[str, pd.DataFrame]:
        """Asynchronously fetch multi-timeframe candles in parallel using asyncio tasks."""
        if timeframes is None:
            timeframes = ['1mo', '1w', '1d', '4h', '1h', '30m', '15m', '5m']

        tasks = [self.fetch_historical_data_async(tf, n_bars=400) for tf in timeframes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        mtf_data = {}
        for tf, res in zip(timeframes, results):
            if isinstance(res, pd.DataFrame) and not res.empty:
                mtf_data[tf] = res
        return mtf_data

    def get_historical_data(self, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Get historical candles synchronously, hit cache first."""
        global _candles_cache
        if self.symbol_key in _candles_cache and timeframe in _candles_cache[self.symbol_key]:
            df = _candles_cache[self.symbol_key][timeframe]
            if df is not None and not df.empty:
                return df

        # Fallback to synchronous fetch
        client = get_tv_client()
        if not client:
            return None
        tv_info = TRADINGVIEW_SYMBOLS.get(self.symbol_key)
        if not tv_info:
            return None
        symbol, exchange = tv_info
        tv_interval = TIMEFRAME_MAP.get(timeframe.lower())
        if not tv_interval:
            return None

        for attempt in range(3):
            try:
                df = client.get_hist(symbol=symbol, exchange=exchange, interval=tv_interval, n_bars=n_bars)
                if df is not None and not df.empty:
                    df = df.copy()
                    df.index.name = 'time'
                    if 'volume' in df.columns:
                        df.rename(columns={'volume': 'tick_volume'}, inplace=True)
                    else:
                        df['tick_volume'] = 0.0

                    for col in ['open', 'high', 'low', 'close', 'tick_volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                    res = df[['open', 'high', 'low', 'close', 'tick_volume']].dropna()
                    
                    if self.symbol_key not in _candles_cache:
                        _candles_cache[self.symbol_key] = {}
                    _candles_cache[self.symbol_key][timeframe] = res
                    return res
            except Exception as e:
                logger.warning(f"Fallback sync fetch failed for {self.symbol_key}: {e}")
                time.sleep(0.1)
        return None

    def get_multi_timeframe_data(self, timeframes: list = None) -> Dict[str, pd.DataFrame]:
        """Fetch candles for multiple timeframes synchronously, returning cache hits instantly."""
        if timeframes is None:
            timeframes = ['1d', '4h', '1h', '30m', '15m', '5m']

        mtf_data = {}
        for tf in timeframes:
            df = self.get_historical_data(tf, n_bars=400)
            if df is not None and not df.empty:
                mtf_data[tf] = df
        return mtf_data
