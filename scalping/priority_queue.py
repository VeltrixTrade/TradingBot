"""
Mustafa Bot - Intelligent Priority Trade Queue
ترتيب وتصنيف الفرص التداولية المكتشفة بناءً على التقييم، نسبة العائد، والأداء التاريخي للاستراتيجية
"""

import logging
from typing import List, Dict
from analytics.strategy_tracker import StrategyPerformanceTracker

logger = logging.getLogger('mustafa_bot.scalping.priority_queue')


class IntelligentTradePriorityQueue:
    """Ranks and sorts overlapping scalping setups to dispatch the strongest opportunity first."""

    def __init__(self):
        self.tracker = StrategyPerformanceTracker()

    def rank_and_sort_setups(self, setups: List[Dict]) -> List[Dict]:
        """Rank candidate setups by composite score and return sorted list."""
        if not setups:
            return []

        ranked_setups = []
        for setup in setups:
            strat_name = setup.get('strategy_name', 'Default')
            score = setup.get('score', 80)
            rr = setup.get('risk_reward', 2.0)

            hist_win_rate = self.tracker.get_strategy_win_rate(strat_name)

            # Composite ranking score formula
            rank_score = (score * 0.45) + (rr * 12.0) + (hist_win_rate * 0.25)
            
            setup['rank_score'] = round(rank_score, 2)
            setup['hist_strategy_winrate'] = round(hist_win_rate, 1)
            ranked_setups.append(setup)

        # Sort descending by rank_score
        ranked_setups.sort(key=lambda x: x['rank_score'], reverse=True)
        logger.info(f"🔀 Priority Trade Queue ranked {len(ranked_setups)} candidate setups")
        return ranked_setups
