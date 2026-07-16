"""
Mustafa Bot - Smart Multi-Source Price Fetcher
جلب الأسعار عبر 4 مستويات: (1) MT5 Native → (2) MT5 Bridge API → (3) TwelveData API (Premium) → (4) yfinance & Binance Fallbacks
"""

import logging
import json
import urllib.request
from typing import Optional, Dict
from datetime import datetime, timezone
import pandas as pd
from data.mt5_connection import MT5ConnectionManager, MT5_AVAILABLE
from config import Config

logger = logging.getLogger('mustafa_bot.data.price_fetcher')

# ── Symbol → Direct REST API mapping ──
DIRECT_API_MAP = {
    'XAU/USD': {'url': 'https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT', 'key': 'price'},
    'BTC/USD': {'url': 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', 'key': 'price'},
    'ETH/USD': {'url': 'https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT', 'key': 'price'},
}

YFINANCE_MAP = {
    'XAU/USD': 'GC=F',
    'EUR/USD': 'EURUSD=X',
    'GBP/USD': 'GBPUSD=X',
    'USD/JPY': 'JPY=X',
    'NAS100': 'NQ=F',
    'US30': 'YM=F',
    'BTC/USD': 'BTC-USD',
    'ETH/USD': 'ETH-USD',
}

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

TWELVEDATA_INTERVAL_MAP = {
    '1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min',
    '1h': '1h', '4h': '4h', '1d': '1day', '1w': '1week', '1mo': '1month',
    'm1': '1min', 'm5': '5min', 'm15': '15min', 'm30': '30min',
    'h1': '1h', 'h4': '4h', 'd1': '1day', 'w1': '1week', 'mn1': '1month'
}


class PriceFetcher:
    """Multi-source price fetcher: MT5 Native → Bridge API → TwelveData → Binance/yfinance."""

    def __init__(self, symbol_key: str = 'XAU/USD'):
        self.symbol_key = symbol_key
        self.mt5_mgr = MT5ConnectionManager()
        self._price_source = 'UNKNOWN'

        if not self.mt5_mgr.is_initialized:
            self.mt5_mgr.connect()

    # ══════════════════════════════════════════════
    #  LIVE CURRENT PRICE
    # ══════════════════════════════════════════════

    def get_current_price(self, chat_id: Optional[int] = None) -> Optional[float]:
        """Get live price via best available source, apply calibration offset if needed."""
        raw_p = self._fetch_raw_current_price()
        if raw_p and chat_id:
            from data.price_calibrator import BrokerPriceCalibrator
            return BrokerPriceCalibrator().apply_offset(raw_p, chat_id, self.symbol_key)
        return raw_p

    def _fetch_raw_current_price(self) -> Optional[float]:
        """Try all sources in priority order: MT5 Native → Bridge → TwelveData → Direct REST APIs → yfinance."""

        # ── Source 1: MT5 Native or Bridge (via MT5ConnectionManager) ──
        try:
            info = self.mt5_mgr.get_symbol_info(self.symbol_key)
            if info and info.get('bid', 0) > 0:
                self._price_source = 'MT5_DIRECT' if MT5_AVAILABLE else 'MT5_BRIDGE'
                return float(info.get('last', 0) or ((info['bid'] + info['ask']) / 2.0))
        except Exception as e:
            logger.debug(f"MT5/Bridge price fetch failed for {self.symbol_key}: {e}")

        # ── Source 2: TwelveData API (Premium Integration) ──
        price_td = self._fetch_from_twelvedata()
        if price_td:
            self._price_source = 'TWELVEDATA'
            return price_td

        # ── Source 3: Direct REST API (Binance for Gold/Crypto) ──
        price_bin = self._fetch_from_direct_api()
        if price_bin:
            self._price_source = 'DIRECT_REST_API'
            return price_bin

        # ── Source 4: yfinance fallback ──
        price_yf = self._fetch_from_yfinance()
        if price_yf:
            self._price_source = 'YFINANCE'
            return price_yf

        logger.error(f"All price sources failed for {self.symbol_key}")
        return None

    def _fetch_from_twelvedata(self) -> Optional[float]:
        """Fetch live price from TwelveData API."""
        apikey = getattr(Config, 'TWELVEDATA_API_KEY', '').strip()
        if not apikey:
            return None

        td_symbol = TWELVEDATA_SYMBOL_MAP.get(self.symbol_key, self.symbol_key.replace('/', ''))
        url = f"https://api.twelvedata.com/price?symbol={td_symbol}&apikey={apikey}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'MustafaBot/3.5'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if 'price' in data:
                    return float(data['price'])
                elif 'message' in data:
                    logger.debug(f"TwelveData price error: {data['message']}")
        except Exception as e:
            logger.debug(f"TwelveData API price fetch failed for {self.symbol_key}: {e}")
        return None

    def _fetch_from_direct_api(self) -> Optional[float]:
        """Fetch from Binance or free FX REST APIs."""
        api_info = DIRECT_API_MAP.get(self.symbol_key)
        if not api_info:
            return None
        try:
            req = urllib.request.Request(api_info['url'], headers={'User-Agent': 'MustafaBot/3.5'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return float(data.get(api_info['key'], 0))
        except Exception as e:
            logger.debug(f"Direct REST API failed for {self.symbol_key}: {e}")
        return None

    def _fetch_from_yfinance(self) -> Optional[float]:
        """Fetch from yfinance as last resort fallback."""
        ticker = YFINANCE_MAP.get(self.symbol_key)
        if not ticker:
            return None
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.fast_info
            price = getattr(info, 'last_price', None) or getattr(info, 'previous_close', None)
            if price and price > 0:
                return float(price)
        except Exception as e:
            logger.debug(f"yfinance failed for {self.symbol_key}: {e}")
        return None

    # ══════════════════════════════════════════════
    #  HISTORICAL CANDLES
    # ══════════════════════════════════════════════

    def get_historical_data(self, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Fetch historical OHLCV candles: MT5/Bridge → TwelveData → yfinance."""

        # ── Source 1: MT5 Native or Bridge ──
        try:
            df = self.mt5_mgr.get_historical_rates(self.symbol_key, timeframe, n_bars)
            if df is not None and not df.empty:
                df.columns = [c.lower() for c in df.columns]
                required = ['open', 'high', 'low', 'close']
                if all(col in df.columns for col in required):
                    df = df.dropna(subset=required)
                    logger.info(f"Fetched {len(df)} candles for {self.symbol_key} ({timeframe}) via MT5/Bridge")
                    return df
        except Exception as e:
            logger.debug(f"MT5/Bridge candles failed for {self.symbol_key} ({timeframe}): {e}")

        # ── Source 2: TwelveData API (Premium Integration) ──
        df_td = self._fetch_candles_twelvedata(timeframe, n_bars)
        if df_td is not None and not df_td.empty:
            logger.info(f"Fetched {len(df_td)} candles for {self.symbol_key} ({timeframe}) via TwelveData")
            return df_td

        # ── Source 3: yfinance fallback ──
        return self._fetch_candles_yfinance(timeframe, n_bars)

    def _fetch_candles_twelvedata(self, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Download candles from TwelveData API."""
        apikey = getattr(Config, 'TWELVEDATA_API_KEY', '').strip()
        if not apikey:
            return None

        td_symbol = TWELVEDATA_SYMBOL_MAP.get(self.symbol_key, self.symbol_key.replace('/', ''))
        td_interval = TWELVEDATA_INTERVAL_MAP.get(timeframe.lower(), '15min')

        url = f"https://api.twelvedata.com/time_series?symbol={td_symbol}&interval={td_interval}&outputsize={n_bars}&apikey={apikey}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'MustafaBot/3.5'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if 'values' in data and data['values']:
                    df = pd.DataFrame(data['values'])
                    df['time'] = pd.to_datetime(df['datetime'])
                    df.set_index('time', inplace=True)
                    df = df.iloc[::-1]  # Reverse to ascending order
                    
                    if 'volume' in df.columns:
                        df = df.rename(columns={'volume': 'tick_volume'})
                    else:
                        df['tick_volume'] = 0

                    for col in ['open', 'high', 'low', 'close', 'tick_volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    return df[['open', 'high', 'low', 'close', 'tick_volume']].dropna()
                elif 'message' in data:
                    logger.debug(f"TwelveData candles error: {data['message']}")
        except Exception as e:
            logger.debug(f"TwelveData API candles fetch failed for {self.symbol_key}: {e}")
        return None

    def _fetch_candles_yfinance(self, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Download candles from yfinance as fallback."""
        ticker = YFINANCE_MAP.get(self.symbol_key)
        if not ticker:
            return None

        tf_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '4h': '1h', '1d': '1d', '1w': '1wk', '1mo': '1mo',
            'm1': '1m', 'm5': '5m', 'm15': '15m', 'm30': '30m',
            'h1': '1h', 'h4': '1h', 'd1': '1d', 'w1': '1wk', 'mn1': '1mo'
        }
        yf_tf = tf_map.get(timeframe.lower(), '15m')

        period_map = {
            '1m': '1d', '5m': '5d', '15m': '5d', '30m': '10d',
            '1h': '30d', '1d': '1y', '1wk': '2y', '1mo': '5y'
        }
        period = period_map.get(yf_tf, '5d')

        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=yf_tf)
            if df is not None and not df.empty:
                df.columns = [c.lower() for c in df.columns]
                for col in ['open', 'high', 'low', 'close']:
                    if col not in df.columns:
                        return None
                if 'volume' in df.columns:
                    df.rename(columns={'volume': 'tick_volume'}, inplace=True)
                else:
                    df['tick_volume'] = 0
                cols = [c for c in ['open', 'high', 'low', 'close', 'tick_volume'] if c in df.columns]
                logger.info(f"Fetched {len(df)} candles for {self.symbol_key} ({timeframe}) via yfinance fallback")
                return df[cols].tail(n_bars)
        except Exception as e:
            logger.debug(f"yfinance candles failed for {self.symbol_key}: {e}")
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
