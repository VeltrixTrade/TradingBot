"""
Mustafa Bot - Trade Lifecycle Management Engine
مراقبة الصفقات الفعالة حياً، تتبع تحولات المراحل (Entry -> TP1 -> BE -> TP2 -> TP3 -> SL)، وأتمتة نقل الستوب لدخول الصفقة
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from database.db_manager import DatabaseManager
from data.price_fetcher import PriceFetcher
from utils.diagnostics import DiagnosticsManager

logger = logging.getLogger('mustafa_bot.trade_management.lifecycle')


class TradeLifecycleEngine:
    """Async background worker for active trade lifecycle state transitions and Break-Even automation."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.diagnostics = DiagnosticsManager()
        self.fetchers: Dict[str, PriceFetcher] = {}
        self.notification_callback: Optional[Callable] = None
        self.is_running = False

    def set_notification_callback(self, callback: Callable) -> None:
        """Set callback to notify users or channel when a trade status changes."""
        self.notification_callback = callback

    def _get_fetcher(self, symbol_key: str) -> PriceFetcher:
        if symbol_key not in self.fetchers:
            self.fetchers[symbol_key] = PriceFetcher(symbol_key)
        return self.fetchers[symbol_key]

    async def run_lifecycle_check(self) -> List[Dict]:
        """Perform a single iteration check across all active trades."""
        active_trades = self.db.get_active_trades()
        if not active_trades:
            return []

        updated_trades = []
        for trade in active_trades:
            symbol = trade['symbol']
            fetcher = self._get_fetcher(symbol)
            current_price = fetcher.get_current_price()

            if not current_price:
                continue

            trade_id = trade['id']
            direction = trade['direction']
            status = trade['status']
            entry = trade['entry']
            stop_loss = trade['stop_loss']
            tp1 = trade['tp1']
            tp2 = trade['tp2']
            tp3 = trade['tp3']

            new_status = status
            notes = ""

            # Update MAE / MFE
            if direction == 'BUY':
                favorable = max(0.0, current_price - entry)
                adverse = max(0.0, entry - current_price)
            else:
                favorable = max(0.0, entry - current_price)
                adverse = max(0.0, current_price - entry)
            
            self.db.update_trade_excursion(trade_id, adverse, favorable)

            # Check Lifecycle State Transitions
            if status == 'WAITING_ENTRY':
                # Check if price filled entry zone
                if (direction == 'BUY' and current_price <= entry * 1.0005) or (direction == 'SELL' and current_price >= entry * 0.9995):
                    new_status = 'ENTRY_EXECUTED'
                    notes = f"Price reached entry level {current_price:.4f}"

            elif status in ['ENTRY_EXECUTED', 'ACTIVE', 'TP1_HIT', 'BREAK_EVEN_ACTIVATED', 'TP2_HIT']:
                if direction == 'BUY':
                    if current_price >= tp3:
                        new_status = 'TP3_HIT'
                        notes = f"TP3 target hit at {current_price:.4f} 🏁 Full Win!"
                    elif current_price >= tp2 and status not in ['TP2_HIT', 'TP3_HIT']:
                        new_status = 'TP2_HIT'
                        notes = f"TP2 target hit at {current_price:.4f} 🎯"
                    elif current_price >= tp1 and status in ['ENTRY_EXECUTED', 'ACTIVE']:
                        new_status = 'TP1_HIT'
                        notes = f"TP1 target hit at {current_price:.4f} 🎯 Automatic Break-Even Recommended!"
                    elif current_price <= stop_loss:
                        new_status = 'SL_HIT'
                        notes = f"Stop Loss hit at {current_price:.4f} 🛑"
                else:  # SELL
                    if current_price <= tp3:
                        new_status = 'TP3_HIT'
                        notes = f"TP3 target hit at {current_price:.4f} 🏁 Full Win!"
                    elif current_price <= tp2 and status not in ['TP2_HIT', 'TP3_HIT']:
                        new_status = 'TP2_HIT'
                        notes = f"TP2 target hit at {current_price:.4f} 🎯"
                    elif current_price <= tp1 and status in ['ENTRY_EXECUTED', 'ACTIVE']:
                        new_status = 'TP1_HIT'
                        notes = f"TP1 target hit at {current_price:.4f} 🎯 Automatic Break-Even Recommended!"
                    elif current_price >= stop_loss:
                        new_status = 'SL_HIT'
                        notes = f"Stop Loss hit at {current_price:.4f} 🛑"

            if new_status != status:
                success = self.db.update_trade_status(trade_id, new_status, trigger_price=current_price, notes=notes)
                if success:
                    trade['status'] = new_status
                    trade['notes'] = notes
                    trade['trigger_price'] = current_price
                    updated_trades.append(trade)

                    self.diagnostics.log_event(
                        module="TradeLifecycle",
                        severity="INFO",
                        description=f"Trade {trade_id} ({symbol}) transitioned: {status} -> {new_status}",
                        details={'trigger_price': current_price, 'notes': notes}
                    )

                    # Trigger break-even adjustment if TP1 hit
                    if new_status == 'TP1_HIT':
                        self.db.update_trade_status(trade_id, 'BREAK_EVEN_ACTIVATED', trigger_price=current_price, notes="SL moved to Entry price (Break-Even)")

                    # Notify external listener if set
                    if self.notification_callback:
                        try:
                            if asyncio.iscoroutinefunction(self.notification_callback):
                                await self.notification_callback(trade, status, new_status, current_price, notes)
                            else:
                                self.notification_callback(trade, status, new_status, current_price, notes)
                        except Exception as cb_err:
                            logger.error(f"Error in lifecycle notification callback: {cb_err}")

        return updated_trades

    async def start_worker_loop(self, check_interval_seconds: int = 15) -> None:
        """Background loop monitoring active trades periodically."""
        self.is_running = True
        logger.info(f"🔄 Active Trade Lifecycle Worker loop started (Interval: {check_interval_seconds}s)")
        
        while self.is_running:
            try:
                await self.run_lifecycle_check()
            except Exception as e:
                logger.error(f"Error in lifecycle worker loop iteration: {e}", exc_info=True)
                self.diagnostics.log_event("TradeLifecycle", "ERROR", f"Lifecycle loop iteration error: {e}")
            await asyncio.sleep(check_interval_seconds)

    def stop_worker_loop(self) -> None:
        """Stop worker loop."""
        self.is_running = False
        logger.info("🛑 Active Trade Lifecycle Worker loop stopped")
