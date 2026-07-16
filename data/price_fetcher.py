"""
Mustafa Bot - Price Data Fetcher
جلب أسعار الذهب الحية من TradingView مع yfinance كمصدر احتياطي
"""

import logging
from typing import Optional, Dict
import pandas as pd
import numpy as np

logger = logging.getLogger('mustafa_bot.data')


class PriceFetcher:
    """Fetches live XAUUSD price data from TradingView via tvdatafeed."""

    def __init__(self, symbol: str = 'XAUUSD', exchange: str = 'OANDA'):
        self.symbol = symbol
        self.exchange = exchange
        self.tv = None
        self.Interval = None
        self.interval_map = {}
        self.source = 'none'
        self._init_tv()

    def _init_tv(self) -> None:
        """Initialize TvDatafeed connection with yfinance fallback."""
        try:
            from tvdatafeed import TvDatafeed, Interval
            self.tv = TvDatafeed()
            self.Interval = Interval
            self.interval_map = {
                '1m': Interval.in_1_minute,
                '5m': Interval.in_5_minute,
                '15m': Interval.in_15_minute,
                '30m': Interval.in_30_minute,
                '1h': Interval.in_1_hour,
                '4h': Interval.in_4_hour,
                '1d': Interval.in_daily,
            }
            self.source = 'tradingview'
            logger.info('📊 TradingView data source initialized')
        except Exception as e:
            logger.warning(f'TvDatafeed unavailable: {e}, falling back to yfinance')
            self.source = 'yfinance'

    def get_historical_data(self, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Get historical OHLCV data with lowercase columns and datetime index."""
        df = None
        active_source = 'unknown'

        if self.source == 'tradingview' and self.tv is not None:
            df = self._fetch_from_tv(timeframe, n_bars)
            if df is not None:
                active_source = 'tradingview'

        if df is None:
            df = self._fetch_from_binance(timeframe, n_bars)
            if df is not None:
                active_source = 'binance'

        if df is None:
            df = self._fetch_from_yfinance(timeframe, n_bars)
            if df is not None:
                active_source = 'yfinance'

        if df is not None and not df.empty:
            df.columns = [c.lower() for c in df.columns]
            # Ensure required columns exist
            required = ['open', 'high', 'low', 'close']
            if not all(col in df.columns for col in required):
                logger.error(f'Missing required columns. Got: {list(df.columns)}')
                return None
            if 'volume' not in df.columns:
                df['volume'] = 0
            # Remove any rows with NaN in OHLC
            df = df.dropna(subset=['open', 'high', 'low', 'close'])
            logger.info(f'Fetched {len(df)} bars for {timeframe} from {active_source}')
        else:
            logger.error(f'Failed to fetch data for {timeframe}')

        return df


    def _fetch_from_tv(self, timeframe: str, n_bars: int) -> Optional[pd.DataFrame]:
        """Fetch data from TradingView."""
        try:
            interval = self.interval_map.get(timeframe)
            if interval is None:
                logger.warning(f'Unsupported TradingView timeframe: {timeframe}')
                return None

            df = self.tv.get_hist(
                symbol=self.symbol,
                exchange=self.exchange,
                interval=interval,
                n_bars=n_bars
            )

            if df is not None and not df.empty:
                # tvdatafeed may return columns with various cases
                df.columns = [c.lower().strip() for c in df.columns]
                # Drop symbol column if present
                if 'symbol' in df.columns:
                    df = df.drop(columns=['symbol'])
                return df

        except Exception as e:
            logger.error(f'TradingView fetch error: {e}')

        return None

    def _fetch_from_binance(self, timeframe: str, n_bars: int) -> Optional[pd.DataFrame]:
        """Fetch real-time Spot Gold price from Binance via PAXGUSDT."""
        try:
            import urllib.request
            import json
            import pandas as pd

            # Map timeframes to Binance intervals
            interval_map = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '4h': '4h',
                '1d': '1d',
                '1w': '1w',
                '1mo': '1M'
            }

            interval = interval_map.get(timeframe)
            if not interval:
                logger.warning(f'Unsupported Binance timeframe: {timeframe}')
                return None

            limit = min(1000, n_bars)
            url = f'https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={interval}&limit={limit}'

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())

            if not data:
                return None

            # Parse Binance response
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
            ])

            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            cols = ['open', 'high', 'low', 'close', 'volume']
            for col in cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            return df[cols]

        except Exception as e:
            logger.error(f'Binance fetch error: {e}')
            return None

    def _fetch_from_yfinance(self, timeframe: str, n_bars: int) -> Optional[pd.DataFrame]:
        """Fetch from yfinance as fallback using GC=F (gold futures)."""
        try:
            import yfinance as yf

            # Map timeframes to yfinance parameters
            tf_map = {
                '1m': ('1m', '7d'),
                '5m': ('5m', '60d'),
                '15m': ('15m', '60d'),
                '30m': ('30m', '60d'),
                '1h': ('1h', '730d'),
                '4h': ('1h', '730d'),  # Fetch 1h and resample
                '1d': ('1d', '3y'),
                '1w': ('1wk', '5y'),
                '1mo': ('1mo', '10y'),
            }

            if timeframe not in tf_map:
                logger.warning(f'Unsupported yfinance timeframe: {timeframe}')
                return None

            yf_interval, yf_period = tf_map[timeframe]
            ticker = yf.Ticker('GC=F')
            df = ticker.history(period=yf_period, interval=yf_interval)

            if df is None or df.empty:
                return None

            df.columns = [c.lower().strip() for c in df.columns]

            # Resample for 4h if needed
            if timeframe == '4h' and yf_interval == '1h':
                df = df.resample('4h').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

            # Limit to n_bars
            if len(df) > n_bars:
                df = df.tail(n_bars)

            return df

        except Exception as e:
            logger.error(f'yfinance fetch error: {e}')

        return None

    def get_current_price(self) -> Optional[float]:
        """Get the latest price of XAUUSD."""
        try:
            df = self.get_historical_data(timeframe='5m', n_bars=5)
            if df is not None and not df.empty:
                return float(df['close'].iloc[-1])
        except Exception as e:
            logger.error(f'Error getting current price: {e}')
        return None

    def get_multi_timeframe_data(self, timeframes: list = None,
                                  n_bars: int = 500) -> Dict[str, pd.DataFrame]:
        """Get data for multiple timeframes."""
        if timeframes is None:
            timeframes = ['5m', '15m', '1h', '4h', '1d']

        data = {}
        for tf in timeframes:
            df = self.get_historical_data(timeframe=tf, n_bars=n_bars)
            if df is not None and not df.empty:
                data[tf] = df
            else:
                logger.warning(f'No data for timeframe {tf}')

        return data
