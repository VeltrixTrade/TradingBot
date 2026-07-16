"""
Mustafa Bot - Pure Native MT5 Price Fetcher
جلب أسعار وعقود التداول الحية والشموع التاريخية مباشرة حصرياً عبر حزمة MetaTrader 5 الرسمية
"""

import logging
from typing import Optional, Dict
import pandas as pd
from data.mt5_connection import MT5ConnectionManager
from config import Config

logger = logging.getLogger('mustafa_bot.data.price_fetcher')


class PriceFetcher:
    """Fetches live MT5 market data, tick spreads, and historical candles for supported instruments directly from MT5 API."""

    def __init__(self, symbol_key: str = 'XAU/USD'):
        self.symbol_key = symbol_key
        self.mt5_mgr = MT5ConnectionManager()
        
        if not self.mt5_mgr.is_initialized:
            self.mt5_mgr.connect()

    def get_historical_data(self, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Fetch historical candle rates directly from MetaTrader 5 terminal."""
        if not self.mt5_mgr.is_initialized:
            self.mt5_mgr.connect()

        df = self.mt5_mgr.get_historical_rates(self.symbol_key, timeframe, n_bars)

        if df is not None and not df.empty:
            df.columns = [c.lower() for c in df.columns]
            required = ['open', 'high', 'low', 'close']
            if not all(col in df.columns for col in required):
                logger.error(f"MT5 DataFrame missing required columns. Got: {list(df.columns)}")
                return None
            
            df = df.dropna(subset=required)
            logger.info(f"📊 [Pure Native MT5] Fetched {len(df)} candles for {self.symbol_key} ({timeframe})")
            return df
        
        logger.warning(f"⚠️ Primary MT5 rate fetch returned empty for {self.symbol_key} ({timeframe}). Retrying connection...")
        self.mt5_mgr.connect()
        return self.mt5_mgr.get_historical_rates(self.symbol_key, timeframe, n_bars)

    def get_multi_timeframe_data(self, timeframes: list = None) -> Dict[str, pd.DataFrame]:
        """Fetch historical candle DataFrames for multiple timeframes simultaneously."""
        if timeframes is None:
            timeframes = ['1mo', '1w', '1d', '4h', '1h', '30m', '15m', '5m']

        mtf_data = {}
        for tf in timeframes:
            df = self.get_historical_data(tf, n_bars=400)
            if df is not None and not df.empty:
                mtf_data[tf] = df
        return mtf_data

    def get_current_price(self, chat_id: Optional[int] = None) -> Optional[float]:
        """Get live current price (Last/Bid/Ask mid) directly from MT5 symbol_info."""
        info = self.mt5_mgr.get_symbol_info(self.symbol_key)
        if info and info.get('last', 0) > 0:
            raw_p = info['last']
            if chat_id:
                from data.price_calibrator import BrokerPriceCalibrator
                return BrokerPriceCalibrator().apply_offset(raw_p, chat_id, self.symbol_key)
            return raw_p
        
        df = self.get_historical_data('15m', n_bars=5)
        if df is not None and not df.empty:
            raw_p = float(df['close'].iloc[-1])
            if chat_id:
                from data.price_calibrator import BrokerPriceCalibrator
                return BrokerPriceCalibrator().apply_offset(raw_p, chat_id, self.symbol_key)
            return raw_p
        return None

    def _fetch_raw_current_price(self) -> Optional[float]:
        """Internal raw price fetcher without offset."""
        info = self.mt5_mgr.get_symbol_info(self.symbol_key)
        if info and info.get('last', 0) > 0:
            return float(info['last'])
        df = self.get_historical_data('15m', n_bars=5)
        if df is not None and not df.empty:
            return float(df['close'].iloc[-1])
        return None
