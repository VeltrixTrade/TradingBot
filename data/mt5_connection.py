"""
Mustafa Bot - TwelveData Connection Adapter (Bypassing MT5)
محول البيانات الذي يعتمد بالكامل على TwelveData ويلغي خيارات MetaTrader 5
"""

import logging
from typing import Dict, Optional, Tuple, List
import pandas as pd
from config import Config
from utils.diagnostics import DiagnosticsManager

logger = logging.getLogger('mustafa_bot.data.mt5_connection')
MT5_AVAILABLE = False
mt5 = None


class MT5ConnectionManager:
    """Connection adaptor that routes all requests exclusively to TwelveData."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5ConnectionManager, cls).__new__(cls)
            cls._instance.is_initialized = True
            cls._instance.active_account_info = {
                'login': 'TradingView OANDA',
                'server': 'Cloud API',
                'company': 'TradingView',
                'balance': 100000.0,
                'equity': 100000.0,
                'leverage': 100
            }
            cls._instance.terminal_info = {
                'ping_last': 15,
                'build': 2026
            }
            cls._instance.diagnostics = DiagnosticsManager()
            cls._instance.broker_symbols = {}
        return cls._instance

    def connect(self, chat_id: Optional[int] = None) -> bool:
        """Mock connect always returning True since TradingView is active."""
        self.is_initialized = True
        self.diagnostics.update_data_feed_status("CONNECTED (TradingView OANDA)")
        return True

    def discover_symbols(self) -> Dict[str, str]:
        return {}

    def get_broker_symbol(self, symbol_key: str) -> str:
        return symbol_key

    def get_symbol_info(self, symbol_key: str) -> Optional[Dict]:
        """Fetch live Bid/Ask/Spread details from TradingView OANDA."""
        from data.price_fetcher import PriceFetcher
        fetcher = PriceFetcher(symbol_key)
        price = fetcher.get_current_price()
        if price is None:
            return None

        # Estimate bid/ask/spread based on default config spread
        sym_cfg = Config.SUPPORTED_SYMBOLS.get(symbol_key, {})
        spread_pips = sym_cfg.get('default_spread', 0.3)
        pip_mult = sym_cfg.get('pip_multiplier', 0.1 if 'XAU' in symbol_key else 0.0001)
        spread_val = spread_pips * pip_mult
        digits = sym_cfg.get('decimal_places', 2)

        bid = price - (spread_val / 2.0)
        ask = price + (spread_val / 2.0)

        return {
            'symbol_key': symbol_key,
            'broker_symbol': symbol_key,
            'bid': round(bid, digits),
            'ask': round(ask, digits),
            'last': price,
            'point': 0.01 if 'XAU' in symbol_key else 0.00001,
            'digits': digits,
            'spread_points': int(spread_pips * 10),
            'spread_pips': spread_pips,
            'contract_size': 100 if 'XAU' in symbol_key else 100000,
            'trade_tick_size': 0.01
        }

    def get_historical_rates(self, symbol_key: str, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Fetch historical candle rates directly from TwelveData."""
        from data.price_fetcher import PriceFetcher
        fetcher = PriceFetcher(symbol_key)
        return fetcher.get_historical_data(timeframe, n_bars)
