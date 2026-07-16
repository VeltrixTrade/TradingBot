"""
Mustafa Bot - Pure Native MetaTrader 5 (MT5) Direct Connection & Data Engine
المزود الأحادي والحي لجميع بيانات الأسعار، الشموع التاريخية، الفوارق السعرية (Spread)، ومواصفات الأصول عبر منصة MetaTrader 5 المباشرة
"""

import os
import logging
import asyncio
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timezone
import pandas as pd
from config import Config
from utils.diagnostics import DiagnosticsManager

logger = logging.getLogger('mustafa_bot.data.mt5_connection')

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 python package not installed or unsupported in current environment")


class MT5ConnectionManager:
    """Singleton lifecycle connection manager for Pure Native MetaTrader 5 terminal integration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5ConnectionManager, cls).__new__(cls)
            cls._instance.is_initialized = False
            cls._instance.active_account_info: Dict = {}
            cls._instance.terminal_info: Dict = {}
            cls._instance.diagnostics = DiagnosticsManager()
            cls._instance.broker_symbols: Dict[str, str] = {}
            cls._instance.tf_map = {}
            cls._instance._init_tf_map()
        return cls._instance

    def _init_tf_map(self) -> None:
        """Initialize timeframe string mapping directly to MT5 API constants."""
        if MT5_AVAILABLE and mt5 is not None:
            self.tf_map = {
                '1m': mt5.TIMEFRAME_M1, '5m': mt5.TIMEFRAME_M5, '15m': mt5.TIMEFRAME_M15,
                '30m': mt5.TIMEFRAME_M30, '1h': mt5.TIMEFRAME_H1, '4h': mt5.TIMEFRAME_H4,
                '1d': mt5.TIMEFRAME_D1, '1w': mt5.TIMEFRAME_W1, '1mo': mt5.TIMEFRAME_MN1,
                'm1': mt5.TIMEFRAME_M1, 'm5': mt5.TIMEFRAME_M5, 'm15': mt5.TIMEFRAME_M15,
                'm30': mt5.TIMEFRAME_M30, 'h1': mt5.TIMEFRAME_H1, 'h4': mt5.TIMEFRAME_H4,
                'd1': mt5.TIMEFRAME_D1, 'w1': mt5.TIMEFRAME_W1, 'mn1': mt5.TIMEFRAME_MN1
            }

    def connect(self, chat_id: Optional[int] = None) -> bool:
        """Establish or verify direct connection to installed MetaTrader 5 terminal."""
        if not MT5_AVAILABLE or mt5 is None:
            self.diagnostics.update_data_feed_status("MT5_PACKAGE_MISSING")
            logger.warning("MetaTrader5 package is unavailable in environment")
            return False

        try:
            init_kwargs = {}
            if Config.MT5_PATH and os.path.exists(Config.MT5_PATH):
                init_kwargs['path'] = Config.MT5_PATH

            login_id = Config.MT5_LOGIN
            if chat_id:
                from database.db_manager import DatabaseManager
                acc_db = DatabaseManager().get_mt5_account(chat_id)
                if acc_db:
                    login_id = acc_db.get('login', login_id)
                    if acc_db.get('server'): init_kwargs['server'] = acc_db['server']
                    if acc_db.get('encrypted_password'):
                        from utils.crypto_vault import CryptoVault
                        init_kwargs['password'] = CryptoVault().decrypt_secret(acc_db['encrypted_password'])

            if login_id > 0:
                init_kwargs['login'] = login_id

            # Initialize MT5 terminal connection
            initialized = mt5.initialize(**init_kwargs)

            if not initialized:
                err_code, err_msg = mt5.last_error()
                logger.error(f"Failed to initialize direct MetaTrader 5 terminal: Code {err_code} ({err_msg})")
                self.diagnostics.log_event("MT5Connection", "ERROR", f"MT5 direct connection failed: {err_msg}")
                self.diagnostics.update_data_feed_status("DISCONNECTED")
                self.is_initialized = False
                return False

            term_raw = mt5.terminal_info()
            acc_raw = mt5.account_info()

            if term_raw is None or acc_raw is None:
                logger.warning("MT5 connected but account/terminal details unavailable")
                self.is_initialized = False
                return False

            self.is_initialized = True
            self.active_account_info = {
                'login': acc_raw.login,
                'server': acc_raw.server,
                'company': acc_raw.company,
                'name': acc_raw.name,
                'currency': acc_raw.currency,
                'balance': acc_raw.balance,
                'equity': acc_raw.equity,
                'margin_free': acc_raw.margin_free,
                'leverage': acc_raw.leverage
            }

            self.terminal_info = {
                'community_account': term_raw.community_account,
                'connected': term_raw.connected,
                'ping_last': term_raw.ping_last,
                'build': term_raw.build,
                'name': term_raw.name,
                'path': term_raw.path,
                'data_path': term_raw.data_path
            }

            ping_ms = round(term_raw.ping_last / 1000.0, 1) if term_raw.ping_last else 0.0
            self.diagnostics.update_data_feed_status(f"CONNECTED (MT5 Direct | {ping_ms}ms)")
            logger.info(f"✅ Pure Native MT5 Terminal Active: Account {acc_raw.login} ({acc_raw.company}) | Ping: {ping_ms}ms | Build: {term_raw.build}")

            # Auto-discover broker symbol names
            self.discover_symbols()
            return True

        except Exception as e:
            logger.error(f"Direct MT5 connection error: {e}", exc_info=True)
            self.is_initialized = False
            self.diagnostics.update_data_feed_status("ERROR")
            return False

    def discover_symbols(self) -> Dict[str, str]:
        """Auto-detect available broker symbols in connected MT5 terminal and map them to standard instrument keys."""
        if not self.is_initialized or mt5 is None:
            return {}

        try:
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                return {}

            avail_names = [s.name for s in all_symbols]
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

            for base_key, options in candidates.items():
                matched = None
                for opt in options:
                    if opt in avail_names:
                        matched = opt
                        break
                    for name in avail_names:
                        if opt.lower() in name.lower():
                            matched = name
                            break
                    if matched: break

                if matched:
                    mt5.symbol_select(matched, True)
                    self.broker_symbols[base_key] = matched

            logger.info(f"🔍 Discovered & mapped {len(self.broker_symbols)} MT5 broker symbols: {self.broker_symbols}")
            return self.broker_symbols
        except Exception as e:
            logger.error(f"Error discovering broker symbols in MT5 terminal: {e}")
            return {}

    def get_broker_symbol(self, symbol_key: str) -> str:
        """Resolve exact broker symbol name from connected MT5 terminal."""
        if symbol_key in self.broker_symbols:
            return self.broker_symbols[symbol_key]
        return symbol_key.replace('/', '')

    def get_symbol_info(self, symbol_key: str) -> Optional[Dict]:
        """Fetch live Bid, Ask, Spread, Point, Digits and Contract Size directly from MT5 symbol_info."""
        if not self.is_initialized or mt5 is None:
            self.connect()

        if not self.is_initialized or mt5 is None:
            return None

        broker_symbol = self.get_broker_symbol(symbol_key)
        info = mt5.symbol_info(broker_symbol)

        if info is None:
            mt5.symbol_select(broker_symbol, True)
            info = mt5.symbol_info(broker_symbol)

        if info is None:
            return None

        bid = info.bid
        ask = info.ask
        last = info.last if info.last > 0 else (bid + ask) / 2.0
        point = info.point
        digits = info.digits
        spread_points = info.spread

        sym_cfg = Config.SUPPORTED_SYMBOLS.get(symbol_key, {})
        pip_mult = sym_cfg.get('pip_multiplier', 0.1 if 'XAU' in symbol_key else 0.0001)
        spread_pips = (spread_points * point) / max(0.000001, pip_mult) if point > 0 else (ask - bid) / max(0.000001, pip_mult)

        return {
            'symbol_key': symbol_key,
            'broker_symbol': broker_symbol,
            'bid': bid,
            'ask': ask,
            'last': last,
            'point': point,
            'digits': digits,
            'spread_points': spread_points,
            'spread_pips': round(spread_pips, 2),
            'contract_size': info.trade_contract_size,
            'trade_tick_size': info.trade_tick_size
        }

    def get_historical_rates(self, symbol_key: str, timeframe: str = '15m', n_bars: int = 500) -> Optional[pd.DataFrame]:
        """Fetch historical candle rates directly from MT5 terminal."""
        if not self.is_initialized or mt5 is None:
            self.connect()

        if not self.is_initialized or mt5 is None:
            return None

        broker_symbol = self.get_broker_symbol(symbol_key)
        mt5_tf = self.tf_map.get(timeframe.lower(), mt5.TIMEFRAME_M15)

        rates = mt5.copy_rates_from_pos(broker_symbol, mt5_tf, 0, n_bars)
        if rates is None or len(rates) == 0:
            logger.warning(f"MT5 terminal returned empty rates for {broker_symbol} ({timeframe})")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low',
            'close': 'close', 'tick_volume': 'tick_volume'
        }, inplace=True)

        return df[['open', 'high', 'low', 'close', 'tick_volume']]
