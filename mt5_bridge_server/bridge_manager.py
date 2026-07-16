"""
Mustafa Bot - Native MetaTrader 5 Bridge Manager
المحرك المحلي الفائق السرعة للربط مع منصة MT5 وجلب التكات والشموع والحساب لخدمة الـ REST API
"""

import os
import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone
import pandas as pd

logger = logging.getLogger('mt5_bridge.manager')

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 python package not installed or unsupported")


class NativeMT5BridgeManager:
    """Singleton Manager connecting local FastAPI Bridge with MT5 Desktop Client."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NativeMT5BridgeManager, cls).__new__(cls)
            cls._instance.is_initialized = False
            cls._instance.broker_symbols: Dict[str, str] = {}
            cls._instance.tf_map = {}
            cls._instance._init_tf_map()
        return cls._instance

    def _init_tf_map(self) -> None:
        """Initialize timeframe mapping to MT5 constants."""
        if MT5_AVAILABLE and mt5 is not None:
            self.tf_map = {
                '1m': mt5.TIMEFRAME_M1, '5m': mt5.TIMEFRAME_M5, '15m': mt5.TIMEFRAME_M15,
                '30m': mt5.TIMEFRAME_M30, '1h': mt5.TIMEFRAME_H1, '4h': mt5.TIMEFRAME_H4,
                '1d': mt5.TIMEFRAME_D1, '1w': mt5.TIMEFRAME_W1, '1mo': mt5.TIMEFRAME_MN1,
                'mn1': mt5.TIMEFRAME_MN1, 'w1': mt5.TIMEFRAME_W1, 'd1': mt5.TIMEFRAME_D1,
                'h4': mt5.TIMEFRAME_H4, 'h1': mt5.TIMEFRAME_H1, 'm30': mt5.TIMEFRAME_M30,
                'm15': mt5.TIMEFRAME_M15, 'm5': mt5.TIMEFRAME_M5, 'm1': mt5.TIMEFRAME_M1
            }

    def connect(self, login: int = 0, password: str = "", server: str = "", path: str = "") -> bool:
        """Connect to local MetaTrader 5 terminal."""
        if not MT5_AVAILABLE or mt5 is None:
            logger.error("MetaTrader5 package missing in environment")
            return False

        try:
            init_kwargs = {}
            if path and os.path.exists(path):
                init_kwargs['path'] = path

            if login > 0:
                init_kwargs['login'] = login
                if password: init_kwargs['password'] = password
                if server: init_kwargs['server'] = server

            initialized = mt5.initialize(**init_kwargs)
            if not initialized:
                err_code, err_msg = mt5.last_error()
                logger.error(f"Failed to initialize local MT5 terminal: Code {err_code} ({err_msg})")
                self.is_initialized = False
                return False

            self.is_initialized = True
            self.discover_symbols()
            logger.info("✅ Native MT5 Bridge Manager connected successfully to terminal")
            return True
        except Exception as e:
            logger.error(f"MT5 Bridge connection exception: {e}")
            self.is_initialized = False
            return False

    def get_health_status(self) -> Dict:
        """Fetch bridge and terminal health diagnostics."""
        if not self.is_initialized or mt5 is None:
            self.connect()

        if not self.is_initialized or mt5 is None:
            return {'status': 'DISCONNECTED', 'mt5_connected': False, 'ping_ms': 0.0}

        term = mt5.terminal_info()
        acc = mt5.account_info()

        ping_ms = round(term.ping_last / 1000.0, 1) if term else 0.0
        return {
            'status': 'ONLINE',
            'mt5_connected': term.connected if term else False,
            'ping_ms': ping_ms,
            'build': term.build if term else 0,
            'broker': acc.company if acc else 'Unknown',
            'server': acc.server if acc else 'Unknown',
            'account_login': acc.login if acc else 0,
            'server_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        }

    def discover_symbols(self) -> Dict[str, str]:
        """Discover available symbols on broker terminal."""
        if not self.is_initialized or mt5 is None:
            return {}

        all_syms = mt5.symbols_get()
        if not all_syms:
            return {}

        names = [s.name for s in all_syms]
        candidates = {
            'XAU/USD': ['XAUUSD', 'XAUUSD.a', 'XAUUSDm', 'GOLD', 'XAUUSD.pro', 'XAUUSD.ecn'],
            'EUR/USD': ['EURUSD', 'EURUSD.a', 'EURUSDm', 'EURUSD.pro'],
            'GBP/USD': ['GBPUSD', 'GBPUSD.a', 'GBPUSDm', 'GBPUSD.pro'],
            'USD/JPY': ['USDJPY', 'USDJPY.a', 'USDJPYm', 'USDJPY.pro'],
            'NAS100': ['NAS100', 'US100', 'USTECH100', 'NAS100USD', 'USTECH'],
            'US30': ['US30', 'DJ30', 'USA30', 'WALLSTREET30', 'US30USD'],
            'BTC/USD': ['BTCUSD', 'BTCUSDT', 'BITCOIN'],
            'ETH/USD': ['ETHUSD', 'ETHUSDT', 'ETHEREUM']
        }

        for key, opts in candidates.items():
            for opt in opts:
                if opt in names:
                    mt5.symbol_select(opt, True)
                    self.broker_symbols[key] = opt
                    break
        return self.broker_symbols

    def get_broker_symbol(self, symbol_key: str) -> str:
        """Map standard key to broker symbol."""
        clean = symbol_key.replace('/', '')
        return self.broker_symbols.get(symbol_key, clean)

    def get_symbol_info(self, symbol_key: str) -> Optional[Dict]:
        """Fetch live ticker info."""
        if not self.is_initialized or mt5 is None:
            self.connect()

        b_sym = self.get_broker_symbol(symbol_key)
        info = mt5.symbol_info(b_sym)
        if info is None:
            mt5.symbol_select(b_sym, True)
            info = mt5.symbol_info(b_sym)

        if info is None:
            return None

        bid = info.bid
        ask = info.ask
        last = info.last if info.last > 0 else (bid + ask) / 2.0
        pip_mult = 0.1 if 'XAU' in symbol_key else 0.0001
        spread_pips = (info.spread * info.point) / max(0.000001, pip_mult) if info.point > 0 else (ask - bid) / max(0.000001, pip_mult)

        return {
            'symbol_key': symbol_key,
            'broker_symbol': b_sym,
            'bid': bid,
            'ask': ask,
            'last': last,
            'point': info.point,
            'digits': info.digits,
            'spread_points': info.spread,
            'spread_pips': round(spread_pips, 2),
            'contract_size': info.trade_contract_size,
            'tick_size': info.trade_tick_size,
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        }

    def get_candles(self, symbol_key: str, timeframe: str = '15m', limit: int = 500) -> Optional[List[Dict]]:
        """Fetch OHLCV candles as list of dicts."""
        if not self.is_initialized or mt5 is None:
            self.connect()

        b_sym = self.get_broker_symbol(symbol_key)
        mt5_tf = self.tf_map.get(timeframe.lower(), mt5.TIMEFRAME_M15)
        rates = mt5.copy_rates_from_pos(b_sym, mt5_tf, 0, limit)

        if rates is None or len(rates) == 0:
            return None

        candles = []
        for r in rates:
            dt_str = datetime.fromtimestamp(r['time'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            candles.append({
                'timestamp': dt_str,
                'time': int(r['time']),
                'open': float(r['open']),
                'high': float(r['high']),
                'low': float(r['low']),
                'close': float(r['close']),
                'tick_volume': int(r['tick_volume'])
            })
        return candles

    def get_account_info(self) -> Optional[Dict]:
        """Fetch MT5 account financial details."""
        if not self.is_initialized or mt5 is None:
            self.connect()

        acc = mt5.account_info()
        if acc is None:
            return None

        return {
            'login': acc.login,
            'company': acc.company,
            'server': acc.server,
            'currency': acc.currency,
            'balance': acc.balance,
            'equity': acc.equity,
            'margin': acc.margin,
            'free_margin': acc.margin_free,
            'leverage': acc.leverage
        }

    def get_positions(self) -> List[Dict]:
        """Fetch active positions."""
        if not self.is_initialized or mt5 is None:
            return []
        pos_list = mt5.positions_get()
        if not pos_list:
            return []

        res = []
        for p in pos_list:
            res.append({
                'ticket': p.ticket,
                'symbol': p.symbol,
                'type': 'BUY' if p.type == 0 else 'SELL',
                'volume': p.volume,
                'price_open': p.price_open,
                'sl': p.sl,
                'tp': p.tp,
                'price_current': p.price_current,
                'profit': p.profit
            })
        return res

    def get_orders(self) -> List[Dict]:
        """Fetch pending orders."""
        if not self.is_initialized or mt5 is None:
            return []
        orders = mt5.orders_get()
        if not orders:
            return []
        res = []
        for o in orders:
            res.append({
                'ticket': o.ticket,
                'symbol': o.symbol,
                'volume_initial': o.volume_initial,
                'price_open': o.price_open,
                'sl': o.sl,
                'tp': o.tp
            })
        return res
