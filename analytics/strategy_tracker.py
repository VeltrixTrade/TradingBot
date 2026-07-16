"""
Mustafa Bot - Individual Strategy Performance & Win-Rate Tracker
متابعة وحفظ إحصائيات الأداء ونسبة نجاح كل استراتيجية تداول على حدة
"""

import logging
from typing import Dict
from database.db_manager import DatabaseManager

logger = logging.getLogger('mustafa_bot.analytics.strategy_tracker')


class StrategyPerformanceTracker:
    """Tracks per-strategy performance stats to continuously optimize trade queue ranking."""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()

    def get_strategy_win_rate(self, strategy_name: str) -> float:
        """Fetch historical win rate percentage for a specific strategy module."""
        try:
            trades = self.db.get_all_trades(limit=300)
            strat_trades = [t for t in trades if strategy_name in t.get('analysis_report', '')]
            closed = [t for t in strat_trades if t['status'] in ['TP1_HIT', 'TP2_HIT', 'TP3_HIT', 'SL_HIT']]
            
            if not closed:
                return 75.0  # Base default assumption for new strategies

            wins = len([t for t in closed if 'TP' in t['status']])
            win_rate = (wins / len(closed)) * 100.0
            return win_rate
        except Exception as e:
            logger.error(f"Error fetching strategy win rate for '{strategy_name}': {e}")
            return 75.0
