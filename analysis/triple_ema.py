"""
Mustafa Bot - Triple EMA Crossover Strategy
استراتيجية تقاطع ثلاثي للمتوسطات المتحركة الأسية (EMA 5, EMA 20, EMA 50)
تُستخدم كطبقة تأكيد نهائية مع تحليل SMC/ICT

المصدر: Yasin Academy | السلسلة: Moving Average - Part 4

القواعد:
  - اتجاه صاعد: EMA5 > EMA20 > EMA50 والشموع فوق الجميع
  - اتجاه هابط: EMA50 > EMA20 > EMA5 والشموع تحت الجميع
  - إشارة أولية: تقاطع EMA5 مع EMA20
  - إشارة تأكيد: تقاطع EMA5 و EMA20 معاً مع EMA50
"""

import logging
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np
import ta

logger = logging.getLogger('mustafa_bot.analysis.triple_ema')


class TripleEMACrossover:
    """Triple EMA Crossover Strategy (EMA 5, EMA 20, EMA 50).

    Used as the final confirmation layer on top of SMC/ICT analysis.
    """

    def __init__(self, fast: int = 5, medium: int = 20, slow: int = 50):
        self.fast_period = fast
        self.medium_period = medium
        self.slow_period = slow

    def analyze(self, df: pd.DataFrame) -> Dict:
        """Run Triple EMA analysis on a dataframe.

        Returns a dict with:
          - trend: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
          - alignment: 'PERFECT_BULL' | 'PERFECT_BEAR' | 'PARTIAL' | 'NONE'
          - initial_signal: dict or None (EMA5 x EMA20 crossover)
          - confirmation_signal: dict or None (EMA5+EMA20 x EMA50 crossover)
          - crossover_direction: 'BUY' | 'SELL' | None
          - ema_values: dict with current EMA values
          - confidence_boost: int (0-20 extra confidence points for signal)
          - description: str (Arabic description)
        """
        if df is None or df.empty or len(df) < self.slow_period + 5:
            return self._empty_result()

        try:
            # Calculate the three EMAs
            ema_fast = ta.trend.ema_indicator(df['close'], window=self.fast_period)
            ema_medium = ta.trend.ema_indicator(df['close'], window=self.medium_period)
            ema_slow = ta.trend.ema_indicator(df['close'], window=self.slow_period)

            # Current values
            current_price = float(df['close'].iloc[-1])
            ema5 = float(ema_fast.iloc[-1])
            ema20 = float(ema_medium.iloc[-1])
            ema50 = float(ema_slow.iloc[-1])

            # Previous values (for crossover detection)
            prev_ema5 = float(ema_fast.iloc[-2])
            prev_ema20 = float(ema_medium.iloc[-2])
            prev_ema50 = float(ema_slow.iloc[-2])

            # 2-bars-ago values (for confirmation detection)
            prev2_ema5 = float(ema_fast.iloc[-3]) if len(df) > self.slow_period + 5 else prev_ema5
            prev2_ema20 = float(ema_medium.iloc[-3]) if len(df) > self.slow_period + 5 else prev_ema20

            # ─── 1. Determine Alignment ───
            alignment, trend = self._determine_alignment(
                current_price, ema5, ema20, ema50
            )

            # ─── 2. Detect Initial Signal (EMA5 x EMA20) ───
            initial_signal = self._detect_initial_signal(
                ema5, ema20, prev_ema5, prev_ema20
            )

            # ─── 3. Detect Confirmation Signal (EMA5+EMA20 x EMA50) ───
            confirmation_signal = self._detect_confirmation_signal(
                ema5, ema20, ema50, prev_ema5, prev_ema20, prev_ema50,
                prev2_ema5, prev2_ema20
            )

            # ─── 4. Determine crossover direction ───
            crossover_direction = None
            if confirmation_signal:
                crossover_direction = confirmation_signal['direction']
            elif initial_signal:
                crossover_direction = initial_signal['direction']

            # ─── 5. Calculate confidence boost ───
            confidence_boost = self._calculate_confidence_boost(
                alignment, initial_signal, confirmation_signal,
                current_price, ema5, ema20, ema50
            )

            # ─── 6. Build Arabic description ───
            description = self._build_description(
                trend, alignment, initial_signal, confirmation_signal,
                ema5, ema20, ema50, current_price
            )

            return {
                'trend': trend,
                'alignment': alignment,
                'initial_signal': initial_signal,
                'confirmation_signal': confirmation_signal,
                'crossover_direction': crossover_direction,
                'ema_values': {
                    'ema_5': round(ema5, 2),
                    'ema_20': round(ema20, 2),
                    'ema_50': round(ema50, 2),
                },
                'confidence_boost': confidence_boost,
                'description': description,
            }

        except Exception as e:
            logger.error(f'Triple EMA analysis error: {e}', exc_info=True)
            return self._empty_result()

    # ─────────────────────────────────────────────
    # Internal methods
    # ─────────────────────────────────────────────

    def _determine_alignment(self, price: float, ema5: float,
                              ema20: float, ema50: float) -> Tuple[str, str]:
        """Determine EMA alignment and trend.

        PERFECT_BULL: Price > EMA5 > EMA20 > EMA50
        PERFECT_BEAR: Price < EMA5 < EMA20 < EMA50
        PARTIAL: Some alignment but not perfect
        NONE: No clear alignment
        """
        if price > ema5 > ema20 > ema50:
            return 'PERFECT_BULL', 'BULLISH'
        elif price < ema5 < ema20 < ema50:
            return 'PERFECT_BEAR', 'BEARISH'
        elif ema5 > ema20 > ema50:
            return 'PARTIAL', 'BULLISH'
        elif ema50 > ema20 > ema5:
            return 'PARTIAL', 'BEARISH'
        else:
            return 'NONE', 'NEUTRAL'

    def _detect_initial_signal(self, ema5: float, ema20: float,
                                prev_ema5: float, prev_ema20: float) -> Optional[Dict]:
        """Detect Initial Signal: EMA5 crosses EMA20.

        Bullish: EMA5 was below EMA20, now above.
        Bearish: EMA5 was above EMA20, now below.
        """
        # Bullish crossover
        if prev_ema5 <= prev_ema20 and ema5 > ema20:
            return {
                'type': 'INITIAL',
                'direction': 'BUY',
                'description_ar': 'إشارة أولية: EMA5 تقاطع صعوداً فوق EMA20 ✅',
            }
        # Bearish crossover
        elif prev_ema5 >= prev_ema20 and ema5 < ema20:
            return {
                'type': 'INITIAL',
                'direction': 'SELL',
                'description_ar': 'إشارة أولية: EMA5 تقاطع هبوطاً تحت EMA20 ✅',
            }
        return None

    def _detect_confirmation_signal(self, ema5: float, ema20: float, ema50: float,
                                      prev_ema5: float, prev_ema20: float, prev_ema50: float,
                                      prev2_ema5: float, prev2_ema20: float) -> Optional[Dict]:
        """Detect Confirmation Signal: EMA5 + EMA20 both cross EMA50.

        Bullish: Both EMA5 and EMA20 cross above EMA50 (within last 2-3 bars).
        Bearish: Both EMA5 and EMA20 cross below EMA50 (within last 2-3 bars).
        """
        # Check if EMA5 recently crossed EMA50
        ema5_crossed_above_50 = (prev_ema5 <= prev_ema50 and ema5 > ema50) or \
                                 (prev2_ema5 <= prev_ema50 and ema5 > ema50)
        ema5_crossed_below_50 = (prev_ema5 >= prev_ema50 and ema5 < ema50) or \
                                 (prev2_ema5 >= prev_ema50 and ema5 < ema50)

        # Check if EMA20 recently crossed EMA50
        ema20_crossed_above_50 = (prev_ema20 <= prev_ema50 and ema20 > ema50)
        ema20_crossed_below_50 = (prev_ema20 >= prev_ema50 and ema20 < ema50)

        # Also check: both currently above/below EMA50 (confirmation after cross)
        both_above = ema5 > ema50 and ema20 > ema50
        both_below = ema5 < ema50 and ema20 < ema50

        # Bullish confirmation
        if (ema5_crossed_above_50 or ema20_crossed_above_50) and both_above:
            return {
                'type': 'CONFIRMATION',
                'direction': 'BUY',
                'description_ar': 'إشارة تأكيد: EMA5 و EMA20 تقاطعا صعوداً فوق EMA50 ✅✅',
            }

        # Bearish confirmation
        if (ema5_crossed_below_50 or ema20_crossed_below_50) and both_below:
            return {
                'type': 'CONFIRMATION',
                'direction': 'SELL',
                'description_ar': 'إشارة تأكيد: EMA5 و EMA20 تقاطعا هبوطاً تحت EMA50 ✅✅',
            }

        return None

    def _calculate_confidence_boost(self, alignment: str, initial: Optional[Dict],
                                      confirmation: Optional[Dict],
                                      price: float, ema5: float,
                                      ema20: float, ema50: float) -> int:
        """Calculate extra confidence points (0-20) from Triple EMA.

        Points breakdown:
          - Perfect alignment: +8
          - Partial alignment: +4
          - Initial signal present: +3
          - Confirmation signal present: +6
          - Price distance from EMA5 (momentum): +3
        """
        boost = 0

        # Alignment bonus
        if alignment == 'PERFECT_BULL' or alignment == 'PERFECT_BEAR':
            boost += 8
        elif alignment == 'PARTIAL':
            boost += 4

        # Initial signal bonus
        if initial:
            boost += 3

        # Confirmation signal bonus (strongest)
        if confirmation:
            boost += 6

        # Momentum bonus: price is clearly separating from EMA5
        ema_range = abs(ema5 - ema50) if ema50 != 0 else 1
        price_momentum = abs(price - ema5) / max(ema_range, 0.01)
        if 0.05 < price_momentum < 0.5:
            boost += 3

        return min(20, boost)

    def _build_description(self, trend: str, alignment: str,
                            initial: Optional[Dict], confirmation: Optional[Dict],
                            ema5: float, ema20: float, ema50: float,
                            price: float) -> str:
        """Build Arabic description of the Triple EMA analysis."""
        trend_map = {
            'BULLISH': 'صاعد 📈',
            'BEARISH': 'هابط 📉',
            'NEUTRAL': 'محايد ↔️',
        }
        alignment_map = {
            'PERFECT_BULL': '🟢 ترتيب مثالي صاعد (السعر > EMA5 > EMA20 > EMA50)',
            'PERFECT_BEAR': '🔴 ترتيب مثالي هابط (السعر < EMA5 < EMA20 < EMA50)',
            'PARTIAL': '🟡 ترتيب جزئي',
            'NONE': '⚪ لا يوجد ترتيب واضح',
        }

        lines = [
            f"📊 Triple EMA Crossover:",
            f"  • الاتجاه: {trend_map.get(trend, 'محايد')}",
            f"  • الترتيب: {alignment_map.get(alignment, 'غير محدد')}",
            f"  • EMA5: {ema5:.2f} | EMA20: {ema20:.2f} | EMA50: {ema50:.2f}",
            f"  • السعر: {price:.2f}",
        ]

        if initial:
            lines.append(f"  ⚡ {initial['description_ar']}")
        if confirmation:
            lines.append(f"  🎯 {confirmation['description_ar']}")

        return '\n'.join(lines)

    def confirms_direction(self, ema_analysis: Dict, smc_direction: str) -> Tuple[bool, str]:
        """Check if Triple EMA confirms or contradicts an SMC/ICT direction.

        Args:
            ema_analysis: Result from self.analyze()
            smc_direction: 'BUY' or 'SELL' from SMC/ICT setup

        Returns:
            (confirmed: bool, reason: str)
        """
        ema_trend = ema_analysis.get('trend', 'NEUTRAL')
        alignment = ema_analysis.get('alignment', 'NONE')
        crossover = ema_analysis.get('crossover_direction')

        # ─── Strong Confirmation ───
        # Perfect alignment + crossover in same direction
        if smc_direction == 'BUY':
            if alignment in ('PERFECT_BULL',) and (crossover == 'BUY' or crossover is None):
                return True, 'تأكيد قوي ✅✅ - ترتيب مثالي صاعد + تقاطع EMA'
            if ema_trend == 'BULLISH':
                return True, 'تأكيد ✅ - الاتجاه صاعد على Triple EMA'
            if ema_trend == 'NEUTRAL':
                return True, 'تأكيد جزئي 🟡 - لا تعارض من Triple EMA'
            # EMA is bearish but SMC says buy
            return False, 'تحذير ⚠️ - Triple EMA يشير لاتجاه هابط يتعارض مع إشارة الشراء'

        elif smc_direction == 'SELL':
            if alignment in ('PERFECT_BEAR',) and (crossover == 'SELL' or crossover is None):
                return True, 'تأكيد قوي ✅✅ - ترتيب مثالي هابط + تقاطع EMA'
            if ema_trend == 'BEARISH':
                return True, 'تأكيد ✅ - الاتجاه هابط على Triple EMA'
            if ema_trend == 'NEUTRAL':
                return True, 'تأكيد جزئي 🟡 - لا تعارض من Triple EMA'
            return False, 'تحذير ⚠️ - Triple EMA يشير لاتجاه صاعد يتعارض مع إشارة البيع'

        return True, 'لا يوجد اتجاه محدد'

    def _empty_result(self) -> Dict:
        return {
            'trend': 'NEUTRAL',
            'alignment': 'NONE',
            'initial_signal': None,
            'confirmation_signal': None,
            'crossover_direction': None,
            'ema_values': {'ema_5': 0, 'ema_20': 0, 'ema_50': 0},
            'confidence_boost': 0,
            'description': 'لا توجد بيانات كافية لتحليل Triple EMA',
        }
