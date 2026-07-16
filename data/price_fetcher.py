"""
Mustafa Bot - Price Data Fetcher (MetaTrader 5 Native Provider)
جلب أسعار وعقود التداول الحية والشموع التاريخية مباشرة حصرياً عبر منصة MetaTrader 5
"""

import logging
from typing import Optional, Dict
import pandas as pd
from data.mt5_connection import MT5ConnectionManager
from config import Config

logger = logging.getLogger('mustafa_bot.data.price_fetcher')


class PriceFetcher:
    """Fetches live MT5 market data, tick spreads, and historical candles for supported instruments."""

    def __init__(self, symbol_key: str = 'XAU/USD'):
        self.symbol_key = symbol_key
        self.mt5_mgr = MT5ConnectionManager()
        
        # Ensure MT5 is connected
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
            logger.info(f"📊 [MT5 Data] Fetched {len(df)} candles for {self.symbol_key} ({timeframe})")
            return df
        
        # Secondary fallback if MT5 is offline/unsupported
        logger.warning(f"⚠️ Primary MT5 rate fetch returned empty for {self.symbol_key} ({timeframe}). Fetching yfinance fallback...")
        return self._fetch_from_yfinance_fallback(timeframe, n_bars)

    def _fetch_from_yfinance_fallback(self, timeframe: str, n_bars: int) -> Optional[pd.DataFrame]:
        """Fallback yfinance fetcher when MT5 terminal is completely unavailable."""
        try:
            import yfinance as yf
            sym_info = Config.SUPPORTED_SYMBOLS.get(self.symbol_key, Config.SUPPORTED_SYMBOLS['XAU/USD'])
            yf_symbol = sym_info.get('yfinance_symbol', 'GC=F')

            tf_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '4h': '1h', '1d': '1d', '1w': '1wk', '1mo': '1mo'
            }
            yf_interval = tf_map.get(timeframe.lower(), '15m')
            period = '5d' if yf_interval in ['1m', '5m', '15m', '30m', '1h'] else '60d'

            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=yf_interval)

            if df is not None and not df.empty:
                df = df.tail(n_bars).copy()
                df.columns = [c.lower() for c in df.columns]
                df.rename(columns={'volume': 'tick_volume'}, inplace=True)
                return df[['open', 'high', 'low', 'close', 'tick_volume']]
        except Exception as e:
            logger.error(f"yfinance fallback error for {self.symbol_key}: {e}")
        return None

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

    def get_current_price(self) -> Optional[float]:
        """Get live current price (Last/Bid/Ask mid) directly from MT5 symbol_info or Real-Time Live Feed."""
        info = self.mt5_mgr.get_symbol_info(self.symbol_key)
        if info and info.get('last', 0) > 0:
            return info['last']
        
        # Fallback to latest live candle close
        df = self.get_historical_data('15m', n_bars=5)
        if df is not None and not df.empty:
            return float(df['close'].iloc[-1])
        return None
