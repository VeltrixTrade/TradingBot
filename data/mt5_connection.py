"""
Mustafa Bot - MetaTrader 5 (MT5) Connection & Data Engine
المزود الأحادي والحي لجميع بيانات الأسعار، الشموع التاريخية، الفوارق السعرية (Spread)، ومواصفات الأصول عبر منصة MetaTrader 5
"""

import os
import logging
import asyncio
from typing import Dict, Optional, Tuple, List
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
    logger.warning("MetaTrader5 python package not installed or unsupported on environment")


class MT5ConnectionManager:
    """Singleton connection manager for MetaTrader 5 live terminal integration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5ConnectionManager, cls).__new__(cls)
            cls._instance.is_initialized = False
            cls._instance.diagnostics = DiagnosticsManager()
            cls._instance.broker_symbols: Dict[str, str] = {}
            cls._instance.tf_map = {}
            cls._instance._init_tf_map()
        return cls._instance

    def _init_tf_map(self) -> None:
        """Initialize timeframe string mapping to MT5 constants."""
        if MT5_AVAILABLE and mt5 is not None:
            self.tf_map = {
                '1m': mt5.TIMEFRAME_M1,
                '5m': mt5.TIMEFRAME_M5,
                '15m': mt5.TIMEFRAME_M15,
                '30m': mt5.TIMEFRAME_M30,
                '1h': mt5.TIMEFRAME_H1,
                '4h': mt5.TIMEFRAME_H4,
                '1d': mt5.TIMEFRAME_D1,
                '1w': mt5.TIMEFRAME_W1,
                '1mo': mt5.TIMEFRAME_MN1,
                'm1': mt5.TIMEFRAME_M1,
                'm5': mt5.TIMEFRAME_M5,
                'm15': mt5.TIMEFRAME_M15,
                'm30': mt5.TIMEFRAME_M30,
                'h1': mt5.TIMEFRAME_H1,
                'h4': mt5.TIMEFRAME_H4,
                'd1': mt5.TIMEFRAME_D1,
                'w1': mt5.TIMEFRAME_W1,
                'mn1': mt5.TIMEFRAME_MN1
            }

    def connect(self) -> bool:
        """Establish or verify MetaTrader 5 terminal connection."""
        if not MT5_AVAILABLE or mt5 is None:
            self.diagnostics.update_data_feed_status("MT5_UNAVAILABLE_ENV")
            logger.warning("MT5 SDK not available in current execution environment")
            return False

        try:
            # Step 1: Initialize connection with path/credentials if provided
            init_kwargs = {}
            if Config.MT5_PATH and os.path.exists(Config.MT5_PATH):
                init_kwargs['path'] = Config.MT5_PATH

            if Config.MT5_LOGIN > 0:
                init_kwargs['login'] = Config.MT5_LOGIN
                if Config.MT5_PASSWORD:
                    init_kwargs['password'] = Config.MT5_PASSWORD
                if Config.MT5_SERVER:
                    init_kwargs['server'] = Config.MT5_SERVER

            initialized = mt5.initialize(**init_kwargs)

            if not initialized:
                err_code, err_msg = mt5.last_error()
                logger.error(f"Failed to initialize MetaTrader 5: Code {err_code} ({err_msg})")
                self.diagnostics.log_event("MT5Connection", "ERROR", f"MT5 connection failed: {err_msg}")
                self.diagnostics.update_data_feed_status("DISCONNECTED")
                self.is_initialized = False
                return False

            term_info = mt5.terminal_info()
            acc_info = mt5.account_info()

            if term_info is None or acc_info is None:
                logger.warning("MT5 connected but account/terminal info unavailable")
                self.is_initialized = False
                return False

            self.is_initialized = True
            self.diagnostics.update_data_feed_status("CONNECTED (MT5 Live)")
            logger.info(f"✅ Connected to MT5 Terminal: Account {acc_info.login} ({acc_info.company}) | Connected: {term_info.connected}")
            
            # Step 2: Auto-discover broker symbol naming
            self.discover_symbols()
            return True

        except Exception as e:
            logger.error(f"MT5 initialization exception: {e}", exc_info=True)
            self.is_initialized = False
            self.diagnostics.update_data_feed_status("ERROR")
            return False

    def discover_symbols(self) -> Dict[str, str]:
        """Auto-detect available broker symbols and map them to standard instrument keys."""
        if not self.is_initialized or mt5 is None:
            return {}

        try:
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                return {}

            avail_names = [s.name for s in all_symbols]
            
            # Base candidates matching
            candidates = {
                'XAU/USD': ['XAUUSD', 'XAUUSD.a', 'XAUUSDm', 'GOLD', 'XAUUSD.pro', 'XAUUSD=X'],
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
                    # Case-insensitive substring match
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
            logger.error(f"Error discovering broker symbols: {e}")
            return {}

    def get_broker_symbol(self, symbol_key: str) -> str:
        """Resolve broker symbol name for standard instrument identifier."""
        if symbol_key in self.broker_symbols:
            return self.broker_symbols[symbol_key]
        # Direct clean fallback (e.g. XAU/USD -> XAUUSD)
        clean = symbol_key.replace('/', '')
        return clean

    def get_symbol_info(self, symbol_key: str) -> Optional[Dict]:
        """Fetch live Bid, Ask, Spread, Point, Digits and Contract Size directly from MT5 symbol_info."""
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

        # Calculate spread in pips
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
        """Fetch historical candle rates directly from MetaTrader 5."""
        if not self.is_initialized or mt5 is None:
            return None

        broker_symbol = self.get_broker_symbol(symbol_key)
        mt5_tf = self.tf_map.get(timeframe.lower(), mt5.TIMEFRAME_M15)

        rates = mt5.copy_rates_from_pos(broker_symbol, mt5_tf, 0, n_bars)
        if rates is None or len(rates) == 0:
            logger.warning(f"MT5 returned no rates for {broker_symbol} ({timeframe})")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Rename columns to standard lowercase format
        df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'tick_volume'
        }, inplace=True)

        return df[['open', 'high', 'low', 'close', 'tick_volume']]
