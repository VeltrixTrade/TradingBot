"""
Mustafa Bot - Ultra-Fast Continuous Market Scanner
ماسح فوري غير متوقف يعمل على فحص جميع الأصول والاستراتيجيات بالتوازي لتقديم أسرع إشارة فورية
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from data.price_fetcher import PriceFetcher
from analysis.strategies.strategy_manager import ParallelStrategyManager
from scalping.priority_queue import IntelligentTradePriorityQueue
from utils.diagnostics import DiagnosticsManager
from config import Config

logger = logging.getLogger('mustafa_bot.scalping.fast_scanner')


class FastMarketScanner:
    """Non-stop continuous parallel market scanner for instant scalping setup detection."""

    def __init__(self):
        self.strategy_manager = ParallelStrategyManager()
        self.priority_queue = IntelligentTradePriorityQueue()
        self.diagnostics = DiagnosticsManager()

        self.fetchers: Dict[str, PriceFetcher] = {}
        self.last_scanned_candles: Dict[str, str] = {}
        self.notification_callback: Optional[Callable] = None
        self.is_scanning = False
        self.selectivity_profile = Config.DEFAULT_SELECTIVITY

    def set_notification_callback(self, callback: Callable) -> None:
        """Set callback to immediately publish signals upon discovery."""
        self.notification_callback = callback

    def set_selectivity_profile(self, profile: str) -> None:
        """Dynamically update selectivity profile (Sniper ➔ Ultra Aggressive)."""
        if profile in Config.SELECTIVITY_PROFILES:
            self.selectivity_profile = profile
            logger.info(f"⚡ Fast Market Scanner selectivity profile set to: {profile}")

    def _get_fetcher(self, symbol_key: str) -> PriceFetcher:
        if symbol_key not in self.fetchers:
            self.fetchers[symbol_key] = PriceFetcher(symbol_key)
        return self.fetchers[symbol_key]

    async def scan_single_symbol(self, symbol_key: str, timeframe: str = '15m') -> List[Dict]:
        """Fetch data and evaluate all strategies in parallel for a single symbol."""
        try:
            fetcher = self._get_fetcher(symbol_key)
            tf_list = ['1mo', '1w', '1d', '4h', '1h', '30m', '15m', '5m']
            data = await fetcher.fetch_multi_timeframe_data_async(tf_list)

            if not data or timeframe not in data:
                return []

            # Check new candle timestamp
            df = data[timeframe]
            last_timestamp = str(df.index[-1]) if not df.empty else ""
            cache_key = f"{symbol_key}_{timeframe}"
            
            # Run parallel strategy evaluations
            setups = await self.strategy_manager.evaluate_all_parallel(
                dataframes=data,
                symbol=symbol_key,
                timeframe=timeframe,
                selectivity_profile=self.selectivity_profile
            )

            self.last_scanned_candles[cache_key] = last_timestamp
            return setups
        except Exception as e:
            logger.error(f"Error scanning symbol '{symbol_key}': {e}")
            return []

    async def run_single_scan_cycle(self) -> List[Dict]:
        """Perform a single parallel scan iteration across all configured symbols."""
        symbols = list(Config.SUPPORTED_SYMBOLS.keys())
        tasks = [self.scan_single_symbol(sym) for sym in symbols]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_candidate_setups = []
        for res in results:
            if isinstance(res, list):
                all_candidate_setups.extend(res)

        if not all_candidate_setups:
            return []

        # Sort candidate setups by priority queue rank
        sorted_setups = self.priority_queue.rank_and_sort_setups(all_candidate_setups)
        return sorted_setups

    async def check_pending_orders_activation(self) -> None:
        """Monitor active pending orders for live price activation, invalidation, or expiration."""
        try:
            from database.db_manager import DatabaseManager
            from datetime import datetime, timezone

            db = DatabaseManager()
            pending_orders = db.get_active_pending_orders()
            if not pending_orders:
                return

            now_utc = datetime.now(timezone.utc)

            for order in pending_orders:
                sym = order['symbol']
                fetcher = self._get_fetcher(sym)
                live_price = fetcher.get_current_price()
                if not live_price:
                    continue

                order_id = order['id']
                entry = order['entry']
                sl = order['stop_loss']
                order_type = order.get('order_type', 'MARKET_BUY')
                direction = order['direction']
                exp_str = order.get('expiration_time', '')

                # 1. Expiration Check
                if exp_str and exp_str != 'N/A (نشط حالياً)':
                    try:
                        # Expiration format: HH:MM UTC (YYYY-MM-DD)
                        exp_dt = datetime.strptime(exp_str, '%H:%M UTC (%Y-%m-%d)').replace(tzinfo=timezone.utc)
                        if now_utc > exp_dt:
                            db.update_trade_status(order_id, 'EXPIRED', trigger_price=live_price, notes="Pending order timed out")
                            logger.info(f"⏳ Pending Order {order_id} ({sym}) EXPIRED")
                            self.diagnostics.log_event("PendingOrderManager", "INFO", f"Order {order_id} ({sym}) expired")
                            continue
                    except Exception:
                        pass

                # 2. Structure Invalidation Check (Price breaches SL before entry)
                if (direction == 'BUY' and live_price <= sl) or (direction == 'SELL' and live_price >= sl):
                    db.update_trade_status(order_id, 'CANCELLED_INVALIDATED', trigger_price=live_price, notes="Structure invalidated (price hit SL before entry)")
                    logger.info(f"🚫 Pending Order {order_id} ({sym}) CANCELLED_INVALIDATED (Hit SL before entry)")
                    self.diagnostics.log_event("PendingOrderManager", "WARNING", f"Pending Order {order_id} ({sym}) invalidated prior to entry")
                    continue

                # 3. Activation Check
                is_activated = False
                if order_type == 'BUY_LIMIT' and live_price <= entry:
                    is_activated = True
                elif order_type == 'SELL_LIMIT' and live_price >= entry:
                    is_activated = True
                elif order_type == 'BUY_STOP' and live_price >= entry:
                    is_activated = True
                elif order_type == 'SELL_STOP' and live_price <= entry:
                    is_activated = True

                if is_activated:
                    db.update_trade_status(order_id, 'ACTIVE', trigger_price=live_price, notes=f"Activated at price {live_price}")
                    logger.info(f"⚡ Pending Order {order_id} ({sym}) ACTIVATED -> Now ACTIVE trade!")
                    self.diagnostics.log_event("PendingOrderManager", "INFO", f"Order {order_id} ({sym}) activated @ {live_price}")

        except Exception as e:
            logger.error(f"Error checking pending orders activation: {e}")

    async def start_continuous_scanner_loop(self, scan_interval_seconds: int = 10) -> None:
        """Background continuous worker loop running non-stop scans."""
        self.is_scanning = True
        logger.info(f"⚡ Ultra-Fast Continuous Market Scanner loop active (Interval: {scan_interval_seconds}s)")

        while self.is_scanning:
            try:
                # Monitor pending order activations & invalidations
                await self.check_pending_orders_activation()

                setups = await self.run_single_scan_cycle()
                self.diagnostics.update_last_analysis_time()

                if setups:
                    # First high-quality opportunity wins!
                    top_setup = setups[0]
                    logger.info(f"🚀 Scanner WINNER setup found: {top_setup['symbol']} ({top_setup['strategy_name']}) - Score: {top_setup['score']}")

                    if self.notification_callback:
                        try:
                            if asyncio.iscoroutinefunction(self.notification_callback):
                                await self.notification_callback(top_setup)
                            else:
                                self.notification_callback(top_setup)
                        except Exception as cb_err:
                            logger.error(f"Error in scanner notification callback: {cb_err}")

            except Exception as e:
                logger.error(f"Error in continuous scanner loop: {e}", exc_info=True)
                self.diagnostics.log_event("FastScanner", "ERROR", f"Scanner loop error: {e}")
            
            await asyncio.sleep(scan_interval_seconds)

    def stop_scanner(self) -> None:
        """Stop background scanner worker loop."""
        self.is_scanning = False
        logger.info("🛑 Ultra-Fast Continuous Market Scanner stopped")
