"""
Mustafa Bot - Signal Filter (5-Stage Pipeline)
فلتر الإشارات المتقدم: 5 مراحل تصفية
"""

import logging
from typing import List
from datetime import datetime, timezone

from signals.models import Signal, SignalType
from config import Config

logger = logging.getLogger('mustafa_bot.signals.filter')


class SignalFilter:
    """5-stage signal filtering pipeline to find only the best signals."""

    def filter_signals(self, signals: List[Signal], market_trend: str = 'NEUTRAL',
                       current_hour_utc: int = None) -> List[Signal]:
        """Run all 5 filter stages and return the best signal(s)."""
        if not signals:
            return []

        if current_hour_utc is None:
            current_hour_utc = datetime.now(timezone.utc).hour

        logger.info(f'📥 Starting filter pipeline with {len(signals)} signals')

        # Stage 1: Trend Filter
        filtered = self._filter_by_trend(signals, market_trend)
        logger.info(f'  Stage 1 (Trend): {len(filtered)} signals passed')
        if not filtered:
            return []

        # Stage 2: Kill Zone Filter
        filtered = self._filter_by_kill_zone(filtered, current_hour_utc)
        logger.info(f'  Stage 2 (Kill Zone): {len(filtered)} signals passed')
        if not filtered:
            return []

        # Stage 3: Confluence Filter
        filtered = self._filter_by_confluence(filtered)
        logger.info(f'  Stage 3 (Confluence): {len(filtered)} signals passed')
        if not filtered:
            return []

        # Stage 4: AI Consensus Filter
        filtered = self._filter_by_ai_consensus(filtered)
        logger.info(f'  Stage 4 (AI Consensus): {len(filtered)} signals passed')
        if not filtered:
            return []

        # Stage 5: Risk/Reward Filter
        filtered = self._filter_by_risk_reward(filtered)
        logger.info(f'  Stage 5 (Risk/Reward): {len(filtered)} signals passed')
        if not filtered:
            return []

        # Select best
        best = self._select_best(filtered)
        logger.info(f'📤 Filter complete: {len(best)} signal(s) selected')

        return best

    def _filter_by_trend(self, signals: List[Signal],
                          market_trend: str) -> List[Signal]:
        """Keep signals that align with higher TF trend."""
        if market_trend == 'NEUTRAL' or market_trend == 'RANGING':
            return signals  # Pass all in ranging/neutral

        result = []
        for s in signals:
            if s.direction.value == 'BUY' and market_trend in ('BULLISH', 'RANGING', 'NEUTRAL'):
                result.append(s)
            elif s.direction.value == 'SELL' and market_trend in ('BEARISH', 'RANGING', 'NEUTRAL'):
                result.append(s)

        return result

    def _filter_by_kill_zone(self, signals: List[Signal],
                              current_hour_utc: int) -> List[Signal]:
        """Keep signals only during active kill zones."""
        in_kill_zone = False
        for zone_name, zone in Config.KILL_ZONES.items():
            start, end = zone['start'], zone['end']
            if start <= end:
                if start <= current_hour_utc < end:
                    in_kill_zone = True
                    break
            else:
                if current_hour_utc >= start or current_hour_utc < end:
                    in_kill_zone = True
                    break

        if in_kill_zone:
            return signals

        # Outside kill zones: only pass very high confidence signals
        return [s for s in signals if s.confidence >= 90]

    def _filter_by_confluence(self, signals: List[Signal]) -> List[Signal]:
        """Keep signals with multiple SMC confluences."""
        result = []
        for s in signals:
            # Check if smc_setup contains '+' (multiple confluences)
            has_multiple = '+' in s.smc_setup
            high_confidence = s.confidence >= 80

            if has_multiple or high_confidence:
                result.append(s)

        return result

    def _filter_by_ai_consensus(self, signals: List[Signal]) -> List[Signal]:
        """Keep signals where enough AI models agree."""
        return [s for s in signals if s.ai_agreement >= Config.MIN_AI_AGREEMENT]

    def _filter_by_risk_reward(self, signals: List[Signal]) -> List[Signal]:
        """Keep signals meeting minimum risk/reward."""
        result = []
        for s in signals:
            if s.type == SignalType.SCALP:
                if s.risk_reward >= Config.MIN_RISK_REWARD_SCALP:
                    result.append(s)
            else:  # SWING
                if s.risk_reward >= Config.MIN_RISK_REWARD_SWING:
                    result.append(s)

        return result

    def _select_best(self, signals: List[Signal]) -> List[Signal]:
        """Sort by confidence descending, return top 1-2 signals."""
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals[:2]
