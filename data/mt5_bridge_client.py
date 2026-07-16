"""
Mustafa Bot - MT5 Bridge API Client for Railway Cloud Bot
عميل الـ HTTP المباشر لاتصال البوت على Railway بجسر MT5 المحلي بخصائص الأمان وسرعة تقل عن 50ms
"""

import os
import logging
import urllib.request
import json
import time
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
            cls._instance._last_health_check = 0.0
            cls._instance._is_bridge_online = False
        return cls._instance

    def is_configured(self) -> bool:
        """Check if bridge URL is configured."""
        return bool(self.base_url)

    def _request(self, endpoint: str, timeout: int = 2) -> Optional[Dict]:
        """Perform raw GET request to MT5 Bridge API."""
        now = time.time()
        # If the bridge was verified to be offline in the last 60 seconds, skip to avoid slow down
        if endpoint != "/health" and not self._is_bridge_online and (now - self._last_health_check < 60):
            return None

        url = f"{self.base_url}{endpoint}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.debug(f"Bridge API request error for {endpoint}: {e}")
            if endpoint == "/health":
                self._is_bridge_online = False
                self._last_health_check = now
        return None

    def get_health(self) -> Optional[Dict]:
        """Query /health endpoint with caching."""
        now = time.time()
        # Return cached status if verified recently to avoid timeout stacking
        if now - self._last_health_check < 30:
            if self._is_bridge_online:
                return {'status': 'ONLINE', 'ping_ms': 50.0}
            return None

        res = self._request("/health", timeout=2)
        self._last_health_check = now
        if res and res.get('status') == 'ONLINE':
            self._is_bridge_online = True
            return res
        else:
            self._is_bridge_online = False
            return None

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
