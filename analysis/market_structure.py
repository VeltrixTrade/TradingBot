"""
Mustafa Bot - Market Structure Analyzer
تحليل هيكل السوق: BOS, CHoCH, Swing Points, Trend
"""

import logging
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger('mustafa_bot.analysis.structure')


class MarketStructureAnalyzer:
    """Analyzes market structure using SMC/ICT methodology."""

    def __init__(self, swing_length: int = 10):
        self.swing_length = swing_length

    def find_swing_highs(self, df: pd.DataFrame) -> pd.Series:
        """Find swing highs - a high higher than swing_length bars on each side."""
        highs = df['high'].values
        n = len(highs)
        swing_highs = pd.Series(False, index=df.index)

        for i in range(self.swing_length, n - self.swing_length):
            window = highs[i - self.swing_length: i + self.swing_length + 1]
            if highs[i] == np.max(window):
                swing_highs.iloc[i] = True

        return swing_highs

    def find_swing_lows(self, df: pd.DataFrame) -> pd.Series:
        """Find swing lows - a low lower than swing_length bars on each side."""
        lows = df['low'].values
        n = len(lows)
        swing_lows = pd.Series(False, index=df.index)

        for i in range(self.swing_length, n - self.swing_length):
            window = lows[i - self.swing_length: i + self.swing_length + 1]
            if lows[i] == np.min(window):
                swing_lows.iloc[i] = True

        return swing_lows

    def detect_bos(self, df: pd.DataFrame, swing_highs: pd.Series,
                   swing_lows: pd.Series) -> List[Dict]:
        """Detect Break of Structure (BOS).
        Bullish BOS: price closes above a previous swing high.
        Bearish BOS: price closes below a previous swing low.
        """
        bos_list = []
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values

        # Get swing high indices and values
        sh_indices = df.index[swing_highs].tolist()
        sh_values = [highs[df.index.get_loc(idx)] for idx in sh_indices]

        # Get swing low indices and values
        sl_indices = df.index[swing_lows].tolist()
        sl_values = [lows[df.index.get_loc(idx)] for idx in sl_indices]

        # Detect bullish BOS (close above swing high)
        for sh_idx, sh_val in zip(sh_indices, sh_values):
            sh_pos = df.index.get_loc(sh_idx)
            # Look for candles after this swing high that close above it
            for j in range(sh_pos + 1, len(df)):
                if closes[j] > sh_val:
                    bos_list.append({
                        'type': 'BULLISH',
                        'level': float(sh_val),
                        'swing_index': sh_pos,
                        'break_index': j,
                        'break_price': float(closes[j]),
                    })
                    break

        # Detect bearish BOS (close below swing low)
        for sl_idx, sl_val in zip(sl_indices, sl_values):
            sl_pos = df.index.get_loc(sl_idx)
            for j in range(sl_pos + 1, len(df)):
                if closes[j] < sl_val:
                    bos_list.append({
                        'type': 'BEARISH',
                        'level': float(sl_val),
                        'swing_index': sl_pos,
                        'break_index': j,
                        'break_price': float(closes[j]),
                    })
                    break

        # Sort by break_index
        bos_list.sort(key=lambda x: x['break_index'])
        return bos_list

    def detect_choch(self, df: pd.DataFrame, swing_highs: pd.Series,
                     swing_lows: pd.Series) -> List[Dict]:
        """Detect Change of Character (CHoCH).
        Bullish CHoCH: In a downtrend (lower lows), price breaks above a swing high.
        Bearish CHoCH: In an uptrend (higher highs), price breaks below a swing low.
        """
        choch_list = []
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        sh_indices = [df.index.get_loc(idx) for idx in df.index[swing_highs]]
        sl_indices = [df.index.get_loc(idx) for idx in df.index[swing_lows]]
        sh_values = [highs[i] for i in sh_indices]
        sl_values = [lows[i] for i in sl_indices]

        # Detect bearish-to-bullish CHoCH
        # Look for series of lower lows, then a break above swing high
        for i in range(2, len(sl_values)):
            if sl_values[i] < sl_values[i - 1] and sl_values[i - 1] < sl_values[i - 2]:
                # We have consecutive lower lows → downtrend
                # Find the nearest swing high after the last lower low
                last_ll_pos = sl_indices[i]
                for sh_pos, sh_val in zip(sh_indices, sh_values):
                    if sh_pos > sl_indices[i - 1] and sh_pos < last_ll_pos:
                        # Check if price breaks above this swing high after the lower low
                        for j in range(last_ll_pos + 1, min(last_ll_pos + 50, len(df))):
                            if closes[j] > sh_val:
                                choch_list.append({
                                    'type': 'BULLISH',
                                    'level': float(sh_val),
                                    'index': j,
                                })
                                break
                        break

        # Detect bullish-to-bearish CHoCH
        for i in range(2, len(sh_values)):
            if sh_values[i] > sh_values[i - 1] and sh_values[i - 1] > sh_values[i - 2]:
                # Consecutive higher highs → uptrend
                last_hh_pos = sh_indices[i]
                for sl_pos, sl_val in zip(sl_indices, sl_values):
                    if sl_pos > sh_indices[i - 1] and sl_pos < last_hh_pos:
                        for j in range(last_hh_pos + 1, min(last_hh_pos + 50, len(df))):
                            if closes[j] < sl_val:
                                choch_list.append({
                                    'type': 'BEARISH',
                                    'level': float(sl_val),
                                    'index': j,
                                })
                                break
                        break

        choch_list.sort(key=lambda x: x['index'])
        return choch_list

    def determine_trend(self, df: pd.DataFrame) -> str:
        """Determine overall trend based on last swing points."""
        swing_highs = self.find_swing_highs(df)
        swing_lows = self.find_swing_lows(df)

        sh_values = df['high'][swing_highs].values
        sl_values = df['low'][swing_lows].values

        if len(sh_values) < 3 or len(sl_values) < 3:
            return 'RANGING'

        # Check last 4 swing points
        recent_sh = sh_values[-4:] if len(sh_values) >= 4 else sh_values
        recent_sl = sl_values[-4:] if len(sl_values) >= 4 else sl_values

        # Higher highs check
        higher_highs = all(recent_sh[i] >= recent_sh[i - 1] for i in range(1, len(recent_sh)))
        # Higher lows check
        higher_lows = all(recent_sl[i] >= recent_sl[i - 1] for i in range(1, len(recent_sl)))
        # Lower highs check
        lower_highs = all(recent_sh[i] <= recent_sh[i - 1] for i in range(1, len(recent_sh)))
        # Lower lows check
        lower_lows = all(recent_sl[i] <= recent_sl[i - 1] for i in range(1, len(recent_sl)))

        if higher_highs and higher_lows:
            return 'BULLISH'
        elif lower_highs and lower_lows:
            return 'BEARISH'
        else:
            return 'RANGING'

    def analyze(self, df: pd.DataFrame) -> Dict:
        """Complete market structure analysis."""
        swing_highs = self.find_swing_highs(df)
        swing_lows = self.find_swing_lows(df)
        bos_list = self.detect_bos(df, swing_highs, swing_lows)
        choch_list = self.detect_choch(df, swing_highs, swing_lows)
        trend = self.determine_trend(df)

        sh_values = df['high'][swing_highs].tolist()
        sl_values = df['low'][swing_lows].tolist()

        last_sh = sh_values[-1] if sh_values else None
        last_sl = sl_values[-1] if sl_values else None

        # Structure strength (0-100)
        strength = 50  # base
        if trend in ('BULLISH', 'BEARISH'):
            strength += 20
        if bos_list:
            recent_bos = [b for b in bos_list if b['break_index'] > len(df) - 50]
            if recent_bos and recent_bos[-1]['type'] == ('BULLISH' if trend == 'BULLISH' else 'BEARISH'):
                strength += 15
        if choch_list:
            strength += 15

        strength = min(100, max(0, strength))

        return {
            'trend': trend,
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'swing_highs_values': sh_values,
            'swing_lows_values': sl_values,
            'bos_list': bos_list,
            'choch_list': choch_list,
            'last_swing_high': last_sh,
            'last_swing_low': last_sl,
            'structure_strength': strength,
        }
