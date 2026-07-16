"""
Mustafa Bot - TwelveData Exclusive Price Fetcher
جلب الأسعار والشموع حصرياً ومباشرة من TwelveData كـ مصدر رئيسي وحيد للبوت
"""

import logging
import json
import urllib.request
from typing import Optional, Dict
import pandas as pd
from config import Config

logger = logging.getLogger('mustafa_bot.data.price_fetcher')

# ── Symbol → Fallback REST API mapping ──
DIRECT_API_MAP = {
    'XAU/USD': {'url': 'https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT', 'key': 'price'},
    'BTC/USD': {'url': 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', 'key': 'price'},
    'ETH/USD': {'url': 'https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT', 'key': 'price'},
}

YFINANCE_MAP = {
    'XAU/USD': 'PAXG-USD',    # Spot Gold tracker (Pax Gold)
    'EUR/USD': 'EURUSD=X',    # Spot Forex
    'GBP/USD': 'GBPUSD=X',    # Spot Forex
    'USD/JPY': 'USDJPY=X',    # Spot Forex
    'NAS100': '^NDX',         # Spot Nasdaq 100 Index
    'US30': '^DJI',           # Spot Dow Jones Index
    'BTC/USD': 'BTC-USD',     # Spot Bitcoin
    'ETH/USD': 'ETH-USD',     # Spot Ethereum
}

TWELVEDATA_SYMBOL_MAP = {
    'XAU/USD': 'XAU/USD',
    'EUR/USD': 'EUR/USD',
    'GBP/USD': 'GBP/USD',
    'USD/JPY': 'USD/JPY',
    'NAS100': 'NDX',
    'US30': 'DJI',
    'BTC/USD': 'BTC/USD',
    'ETH/USD': 'ETH-USD',
}

TWELVEDATA_INTERVAL_MAP = {
    '1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min',
    '1h': '1h', '4h': '4h', '1d': '1day', '1w': '1week', '1mo': '1month',
    'm1': '1min', 'm5': '5min', 'm15': '15min', 'm30': '30min',
    'h1': '1h', 'h4': '4h', 'd1': '1day', 'w1': '1week', 'mn1': '1month'
}


class PriceFetcher:
    """Exclusive TwelveData Price Fetcher (with yfinance/Binance fallback)."""

    def __init__(self, symbol_key: str = 'XAU/USD'):
        self.symbol_key = symbol_key
        self._price_source = 'UNKNOWN'

    # ══════════════════════════════════════════════
    #  LIVE CURRENT PRICE
    # ══════════════════════════════════════════════

    def get_current_price(self, chat_id: Optional[int] = None) -> Optional[float]:
        """Get live price via TwelveData, apply calibration offset if needed."""
        raw_p = self._fetch_raw_current_price()
        if raw_p and chat_id:
            from data.price_calibrator import BrokerPriceCalibrator
            return BrokerPriceCalibrator().apply_offset(raw_p, chat_id, self.symbol_key)
        return raw_p

    def _fetch_raw_current_price(self) -> Optional[float]:
        """Fetch price: TwelveData (Primary) → Binance/yfinance (Emergency Fallback)."""

        # ── Source 1: TwelveData API (Exclusive Primary) ──
        price_td = self._fetch_from_twelvedata()
        if price_td:
            self._price_source = 'TWELVEDATA'
            return price_td

        # ── Source 2: Direct REST API Fallback (Binance for Gold/Crypto) ──
        price_bin = self._fetch_from_direct_api()
        if price_bin:
            self._price_source = 'BINANCE_FALLBACK'
            return price_bin

        # ── Source 3: yfinance Fallback ──
        price_yf = self._fetch_from_yfinance()
        if price_yf:
            self._price_source = 'YFINANCE_FALLBACK'
            return price_yf

        logger.error(f"All price sources failed for {self.symbol_key}")
        return None

    def _fetch_from_twelvedata(self) -> Optional[float]:
        """Fetch live price from TwelveData API."""
        apikey = getattr(Config, 'TWELVEDATA_API_KEY', '').strip()
        if not apikey:
            logger.warning("TwelveData API key is missing in config.")
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
        """Fetch historical OHLCV candles: TwelveData (Primary) → yfinance (Fallback)."""

        # ── Source 1: TwelveData API (Exclusive Primary) ──
        df_td = self._fetch_candles_twelvedata(timeframe, n_bars)
        if df_td is not None and not df_td.empty:
            logger.info(f"Fetched {len(df_td)} candles for {self.symbol_key} ({timeframe}) via TwelveData")
            return df_td

        # ── Source 2: yfinance Fallback ──
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
