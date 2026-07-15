"""
Mustafa Bot - Order Block Detector
كشف وتحليل أوردر بلوكات المؤسسات
"""

import logging
from typing import List, Dict
import pandas as pd
import numpy as np

logger = logging.getLogger('mustafa_bot.analysis.ob')


class OrderBlockDetector:
    """Detects institutional order blocks using SMC methodology."""

    def __init__(self, strength_threshold: int = 5):
        self.strength_threshold = strength_threshold

    def detect_bullish_ob(self, df: pd.DataFrame, bos_list: List[Dict]) -> List[Dict]:
        """Detect bullish order blocks.
        A bullish OB is the last bearish candle before a bullish BOS.
        """
        obs = []
        opens = df['open'].values
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values

        bullish_bos = [b for b in bos_list if b['type'] == 'BULLISH']

        for bos in bullish_bos:
            bos_idx = bos['break_index']
            # Look backward from the BOS candle to find the last bearish candle
            for i in range(bos_idx - 1, max(bos_idx - 20, 0), -1):
                if closes[i] < opens[i]:  # Bearish candle
                    ob_top = float(opens[i])
                    ob_bottom = float(closes[i])
                    strength = self.calculate_ob_strength(df, {
                        'top': ob_top, 'bottom': ob_bottom, 'index': i
                    }, bos_idx)
                    mitigated = self.check_mitigation(df, {
                        'type': 'BULLISH', 'top': ob_top, 'bottom': ob_bottom, 'index': i
                    })
                    obs.append({
                        'type': 'BULLISH',
                        'top': ob_top,
                        'bottom': ob_bottom,
                        'index': i,
                        'strength': strength,
                        'mitigated': mitigated,
                    })
                    break

        return obs

    def detect_bearish_ob(self, df: pd.DataFrame, bos_list: List[Dict]) -> List[Dict]:
        """Detect bearish order blocks.
        A bearish OB is the last bullish candle before a bearish BOS.
        """
        obs = []
        opens = df['open'].values
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values

        bearish_bos = [b for b in bos_list if b['type'] == 'BEARISH']

        for bos in bearish_bos:
            bos_idx = bos['break_index']
            for i in range(bos_idx - 1, max(bos_idx - 20, 0), -1):
                if closes[i] > opens[i]:  # Bullish candle
                    ob_top = float(closes[i])
                    ob_bottom = float(opens[i])
                    strength = self.calculate_ob_strength(df, {
                        'top': ob_top, 'bottom': ob_bottom, 'index': i
                    }, bos_idx)
                    mitigated = self.check_mitigation(df, {
                        'type': 'BEARISH', 'top': ob_top, 'bottom': ob_bottom, 'index': i
                    })
                    obs.append({
                        'type': 'BEARISH',
                        'top': ob_top,
                        'bottom': ob_bottom,
                        'index': i,
                        'strength': strength,
                        'mitigated': mitigated,
                    })
                    break

        return obs

    def calculate_ob_strength(self, df: pd.DataFrame, ob: Dict,
                               bos_candle_idx: int) -> int:
        """Score OB strength 1-10."""
        score = 0
        opens = df['open'].values
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['volume'].values if 'volume' in df.columns else np.ones(len(df))

        ob_idx = ob['index']

        # 1. Impulse size after OB (0-4 points)
        if bos_candle_idx < len(df):
            impulse_size = abs(closes[bos_candle_idx] - closes[ob_idx])
            avg_candle = np.mean(np.abs(closes - opens)[-100:])
            if avg_candle > 0:
                impulse_ratio = impulse_size / avg_candle
                score += min(4, int(impulse_ratio))

        # 2. Volume on OB candle vs average (0-2 points)
        if np.sum(volumes) > 0:
            avg_vol = np.mean(volumes[max(0, ob_idx - 50):ob_idx]) if ob_idx > 0 else np.mean(volumes)
            if avg_vol > 0 and volumes[ob_idx] > avg_vol * 1.5:
                score += 2
            elif avg_vol > 0 and volumes[ob_idx] > avg_vol:
                score += 1

        # 3. First touch (0-2 points) - has price not returned to OB yet?
        ob_top = ob['top']
        ob_bottom = ob['bottom']
        touched = False
        for j in range(ob_idx + 1, len(df)):
            if lows[j] <= ob_top and highs[j] >= ob_bottom:
                touched = True
                break
        if not touched:
            score += 2

        # 4. Candle body size relative to average (0-2 points)
        ob_body = abs(ob['top'] - ob['bottom'])
        avg_body = np.mean(np.abs(closes - opens)[-50:])
        if avg_body > 0 and ob_body > avg_body * 1.5:
            score += 2
        elif avg_body > 0 and ob_body > avg_body:
            score += 1

        return max(1, min(10, score))

    def check_mitigation(self, df: pd.DataFrame, ob: Dict) -> bool:
        """Check if the OB has been mitigated (price body entered the zone)."""
        opens = df['open'].values
        closes = df['close'].values
        ob_idx = ob['index']
        ob_top = ob['top']
        ob_bottom = ob['bottom']

        for j in range(ob_idx + 1, len(df)):
            candle_body_top = max(opens[j], closes[j])
            candle_body_bottom = min(opens[j], closes[j])

            if ob['type'] == 'BULLISH':
                # Mitigated if a candle body closes inside or below the OB
                if candle_body_bottom < ob_bottom:
                    return True
            else:  # BEARISH
                # Mitigated if a candle body closes inside or above the OB
                if candle_body_top > ob_top:
                    return True

        return False

    def get_active_order_blocks(self, df: pd.DataFrame,
                                 bos_list: List[Dict]) -> List[Dict]:
        """Get all active (non-mitigated) order blocks sorted by strength."""
        bullish_obs = self.detect_bullish_ob(df, bos_list)
        bearish_obs = self.detect_bearish_ob(df, bos_list)

        all_obs = bullish_obs + bearish_obs
        active = [ob for ob in all_obs if not ob['mitigated']]
        active.sort(key=lambda x: x['strength'], reverse=True)

        return active
