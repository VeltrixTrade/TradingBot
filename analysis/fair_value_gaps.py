"""
Mustafa Bot - Fair Value Gap Detector
كشف فجوات القيمة العادلة (FVG) ونسبة الملء
"""

import logging
from typing import List, Dict
import pandas as pd
import numpy as np

logger = logging.getLogger('mustafa_bot.analysis.fvg')


class FairValueGapDetector:
    """Detects Fair Value Gaps using ICT methodology."""

    def detect_bullish_fvg(self, df: pd.DataFrame) -> List[Dict]:
        """Detect bullish FVG (3-candle pattern).
        Bullish FVG: candle[i-2].high < candle[i].low (gap between).
        """
        fvgs = []
        highs = df['high'].values
        lows = df['low'].values

        for i in range(2, len(df)):
            if highs[i - 2] < lows[i]:
                fvg = {
                    'type': 'BULLISH',
                    'top': float(lows[i]),
                    'bottom': float(highs[i - 2]),
                    'index': i - 1,  # middle candle
                    'fill_percentage': 0.0,
                }
                fvg['fill_percentage'] = self.calculate_fill_percentage(df, fvg)
                fvgs.append(fvg)

        return fvgs

    def detect_bearish_fvg(self, df: pd.DataFrame) -> List[Dict]:
        """Detect bearish FVG (3-candle pattern).
        Bearish FVG: candle[i].high < candle[i-2].low (gap between).
        """
        fvgs = []
        highs = df['high'].values
        lows = df['low'].values

        for i in range(2, len(df)):
            if highs[i] < lows[i - 2]:
                fvg = {
                    'type': 'BEARISH',
                    'top': float(lows[i - 2]),
                    'bottom': float(highs[i]),
                    'index': i - 1,
                    'fill_percentage': 0.0,
                }
                fvg['fill_percentage'] = self.calculate_fill_percentage(df, fvg)
                fvgs.append(fvg)

        return fvgs

    def calculate_fill_percentage(self, df: pd.DataFrame, fvg: Dict) -> float:
        """Calculate what percentage of the FVG has been filled."""
        fvg_top = fvg['top']
        fvg_bottom = fvg['bottom']
        fvg_size = fvg_top - fvg_bottom

        if fvg_size <= 0:
            return 100.0

        fvg_idx = fvg['index']
        highs = df['high'].values
        lows = df['low'].values

        max_fill = 0.0

        for j in range(fvg_idx + 2, len(df)):
            if fvg['type'] == 'BULLISH':
                # Price retracing down into a bullish FVG
                if lows[j] < fvg_top:
                    penetration = fvg_top - max(lows[j], fvg_bottom)
                    fill = (penetration / fvg_size) * 100.0
                    max_fill = max(max_fill, fill)
            else:  # BEARISH
                # Price retracing up into a bearish FVG
                if highs[j] > fvg_bottom:
                    penetration = min(highs[j], fvg_top) - fvg_bottom
                    fill = (penetration / fvg_size) * 100.0
                    max_fill = max(max_fill, fill)

        return min(100.0, max(0.0, max_fill))

    def get_unfilled_fvgs(self, df: pd.DataFrame) -> List[Dict]:
        """Get FVGs that are less than 50% filled, sorted by recency."""
        bullish = self.detect_bullish_fvg(df)
        bearish = self.detect_bearish_fvg(df)

        all_fvgs = bullish + bearish
        unfilled = [f for f in all_fvgs if f['fill_percentage'] < 50.0]

        # Sort by index descending (newest first)
        unfilled.sort(key=lambda x: x['index'], reverse=True)

        return unfilled
