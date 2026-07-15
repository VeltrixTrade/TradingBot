"""
Mustafa Bot - Liquidity Analyzer
تحليل مناطق السيولة واصطياد وقف الخسارة
"""

import logging
from typing import List, Dict
import pandas as pd
import numpy as np

logger = logging.getLogger('mustafa_bot.analysis.liquidity')


class LiquidityAnalyzer:
    """Analyzes liquidity zones using ICT methodology."""

    def __init__(self, equal_level_tolerance: float = 0.5):
        """tolerance is in price points (e.g., 0.5 for gold = $0.50)."""
        self.tolerance = equal_level_tolerance

    def find_equal_highs(self, df: pd.DataFrame,
                          swing_highs: pd.Series) -> List[Dict]:
        """Find equal highs (buy-side liquidity pools)."""
        highs = df['high'].values
        sh_indices = [df.index.get_loc(idx) for idx in df.index[swing_highs]]
        sh_values = [highs[i] for i in sh_indices]

        equal_groups = []
        used = set()

        for i in range(len(sh_values)):
            if i in used:
                continue
            group = [i]
            for j in range(i + 1, len(sh_values)):
                if j in used:
                    continue
                if abs(sh_values[i] - sh_values[j]) <= self.tolerance:
                    group.append(j)
                    used.add(j)

            if len(group) >= 2:
                used.add(i)
                level = float(np.mean([sh_values[k] for k in group]))
                indices = [sh_indices[k] for k in group]
                equal_groups.append({
                    'type': 'BUY_SIDE',
                    'level': level,
                    'count': len(group),
                    'indices': indices,
                })

        return equal_groups

    def find_equal_lows(self, df: pd.DataFrame,
                         swing_lows: pd.Series) -> List[Dict]:
        """Find equal lows (sell-side liquidity pools)."""
        lows = df['low'].values
        sl_indices = [df.index.get_loc(idx) for idx in df.index[swing_lows]]
        sl_values = [lows[i] for i in sl_indices]

        equal_groups = []
        used = set()

        for i in range(len(sl_values)):
            if i in used:
                continue
            group = [i]
            for j in range(i + 1, len(sl_values)):
                if j in used:
                    continue
                if abs(sl_values[i] - sl_values[j]) <= self.tolerance:
                    group.append(j)
                    used.add(j)

            if len(group) >= 2:
                used.add(i)
                level = float(np.mean([sl_values[k] for k in group]))
                indices = [sl_indices[k] for k in group]
                equal_groups.append({
                    'type': 'SELL_SIDE',
                    'level': level,
                    'count': len(group),
                    'indices': indices,
                })

        return equal_groups

    def detect_liquidity_sweep(self, df: pd.DataFrame,
                                liquidity_levels: List[Dict]) -> List[Dict]:
        """Detect when price sweeps a liquidity zone and reverses.
        A sweep: wick exceeds the level but candle closes back inside.
        """
        sweeps = []
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        opens = df['open'].values

        for liq in liquidity_levels:
            level = liq['level']
            liq_type = liq['type']
            last_idx = max(liq.get('indices', [0]))

            for j in range(last_idx + 1, len(df)):
                if liq_type == 'BUY_SIDE':
                    # Buy-side sweep: wick goes above level but closes below
                    if highs[j] > level and closes[j] < level:
                        # Check for reversal (next candle is bearish)
                        reversal = False
                        if j + 1 < len(df) and closes[j + 1] < opens[j + 1]:
                            reversal = True
                        sweeps.append({
                            'level': level,
                            'sweep_index': j,
                            'direction': 'BUY_SIDE',
                            'reversal': reversal,
                            'sweep_high': float(highs[j]),
                        })
                        break
                else:  # SELL_SIDE
                    # Sell-side sweep: wick goes below level but closes above
                    if lows[j] < level and closes[j] > level:
                        reversal = False
                        if j + 1 < len(df) and closes[j + 1] > opens[j + 1]:
                            reversal = True
                        sweeps.append({
                            'level': level,
                            'sweep_index': j,
                            'direction': 'SELL_SIDE',
                            'reversal': reversal,
                            'sweep_low': float(lows[j]),
                        })
                        break

        return sweeps

    def get_liquidity_pools(self, df: pd.DataFrame, swing_highs: pd.Series,
                             swing_lows: pd.Series) -> Dict:
        """Get all current liquidity pools above and below current price."""
        current_price = float(df['close'].iloc[-1])

        buy_side = self.find_equal_highs(df, swing_highs)
        sell_side = self.find_equal_lows(df, swing_lows)

        # Filter: buy_side above current price, sell_side below
        buy_above = [l for l in buy_side if l['level'] > current_price]
        sell_below = [l for l in sell_side if l['level'] < current_price]

        # Sort by distance from current price
        buy_above.sort(key=lambda x: x['level'])
        sell_below.sort(key=lambda x: x['level'], reverse=True)

        # Detect sweeps
        all_levels = buy_side + sell_side
        sweeps = self.detect_liquidity_sweep(df, all_levels)

        return {
            'buy_side': buy_above,
            'sell_side': sell_below,
            'all_levels': buy_side + sell_side,
            'sweeps': sweeps,
            'current_price': current_price,
        }
