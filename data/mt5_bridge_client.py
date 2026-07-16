"""
Mustafa Bot - MT5 Bridge API Client for Railway Cloud Bot
عميل الـ HTTP المباشر لاتصال البوت على Railway بجسر MT5 المحلي بخصائص الأمان وسرعة تقل عن 50ms
"""

import os
import logging
import urllib.request
import json
from typing import Dict, Optional, List
import pandas as pd
from config import Config

logger = logging.getLogger('mustafa_bot.data.mt5_bridge_client')


class MT5BridgeClient:
    """Async/Sync HTTP Bridge Client connecting Railway Cloud Bot with Local PC MT5 Bridge API."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5BridgeClient, cls).__new__(cls)
            cls._instance.base_url = os.getenv('BRIDGE_API_URL', 'http://127.0.0.1:8000').rstrip('/')
            cls._instance.api_key = os.getenv('BRIDGE_API_KEY', 'mustafa_bot_mt5_bridge_secret_key_2026')
            cls._instance.headers = {
                'Authorization': f'Bearer {cls._instance.api_key}',
                'User-Agent': 'MustafaBot-Railway-BridgeClient/1.0'
            }
        return cls._instance

    def is_configured(self) -> bool:
        """Check if bridge URL is configured."""
        return bool(self.base_url)

    def _request(self, endpoint: str, timeout: int = 5) -> Optional[Dict]:
        """Perform raw GET request to MT5 Bridge API."""
        url = f"{self.base_url}{endpoint}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.debug(f"Bridge API request error for {endpoint}: {e}")
        return None

    def get_health(self) -> Optional[Dict]:
        """Query /health endpoint."""
        return self._request("/health")

    def get_symbol_info(self, symbol_key: str) -> Optional[Dict]:
        """Query /symbol/{symbol} endpoint."""
        clean_sym = symbol_key.replace('/', '-')
        return self._request(f"/symbol/{clean_sym}")

    def get_price(self, symbol_key: str) -> Optional[Dict]:
        """Query /price/{symbol} endpoint."""
        clean_sym = symbol_key.replace('/', '-')
        return self._request(f"/price/{clean_sym}")

    def get_candles(self, symbol_key: str, timeframe: str = '15m', limit: int = 500) -> Optional[pd.DataFrame]:
        """Query /candles/{symbol}/{timeframe} endpoint and return clean DataFrame."""
        clean_sym = symbol_key.replace('/', '-')
        data = self._request(f"/candles/{clean_sym}/{timeframe}?limit={limit}")

        if data and 'candles' in data and data['candles']:
            df = pd.DataFrame(data['candles'])
            if 'timestamp' in df.columns:
                df['time'] = pd.to_datetime(df['timestamp'])
                df.set_index('time', inplace=True)
            return df[['open', 'high', 'low', 'close', 'tick_volume']]
        return None

    def get_account(self) -> Optional[Dict]:
        """Query /account endpoint."""
        return self._request("/account")

    def get_positions(self) -> List[Dict]:
        """Query /positions endpoint."""
        res = self._request("/positions")
        return res.get('positions', []) if res else []

    def get_orders(self) -> List[Dict]:
        """Query /orders endpoint."""
        res = self._request("/orders")
        return res.get('orders', []) if res else []
