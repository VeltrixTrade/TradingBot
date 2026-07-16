"""
Mustafa Bot - Technical Indicators
مؤشرات فنية مساعدة: RSI, ATR, EMA, Volume Profile
"""

import logging
from typing import Dict, List
import pandas as pd
import numpy as np
import ta

logger = logging.getLogger('mustafa_bot.analysis.indicators')


class TechnicalIndicators:
    """Technical indicators using the ta library."""

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI."""
        return ta.momentum.rsi(df['close'], window=period)

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        return ta.volatility.average_true_range(
            df['high'], df['low'], df['close'], window=period
        )

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int = 50) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return ta.trend.ema_indicator(df['close'], window=period)

    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, bins: int = 20) -> Dict:
        """Simple volume profile - high/low volume nodes."""
        price_range = df['high'].max() - df['low'].min()
        if price_range <= 0:
            return {'levels': [], 'volumes': [], 'hvn': [], 'lvn': []}

        bin_edges = np.linspace(df['low'].min(), df['high'].max(), bins + 1)
        volumes_per_bin = np.zeros(bins)
        levels = []

        for i in range(bins):
            bin_low = bin_edges[i]
            bin_high = bin_edges[i + 1]
            level = (bin_low + bin_high) / 2.0
            levels.append(float(level))

            # Count volume where price traded through this level
            mask = (df['low'] <= bin_high) & (df['high'] >= bin_low)
            vol = df.loc[mask, 'volume'].sum() if 'volume' in df.columns else mask.sum()
            volumes_per_bin[i] = float(vol)

        volumes = volumes_per_bin.tolist()
        avg_vol = np.mean(volumes_per_bin) if len(volumes_per_bin) > 0 else 0

        hvn = [levels[i] for i in range(len(levels)) if volumes_per_bin[i] > avg_vol * 1.5]
        lvn = [levels[i] for i in range(len(levels)) if volumes_per_bin[i] < avg_vol * 0.5]

        return {
            'levels': levels,
            'volumes': volumes,
            'hvn': hvn,
            'lvn': lvn,
        }

    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict:
        """Dynamic support/resistance levels based on pivot points."""
        supports = []
        resistances = []

        highs = df['high'].values
        lows = df['low'].values

        half = window // 2

        for i in range(half, len(df) - half):
            # Resistance: local maximum
            if highs[i] == np.max(highs[i - half:i + half + 1]):
                resistances.append(float(highs[i]))

            # Support: local minimum
            if lows[i] == np.min(lows[i - half:i + half + 1]):
                supports.append(float(lows[i]))

        # Remove duplicates within tolerance
        supports = _deduplicate_levels(supports, tolerance=1.0)
        resistances = _deduplicate_levels(resistances, tolerance=1.0)

        # Sort
        supports.sort()
        resistances.sort()

        return {
            'support_levels': supports[-5:],  # Last 5 nearest
            'resistance_levels': resistances[-5:],
        }

    @staticmethod
    def get_market_volatility(df: pd.DataFrame) -> str:
        """Classify market volatility based on ATR/price ratio."""
        atr = TechnicalIndicators.calculate_atr(df)
        if atr is None or atr.empty:
            return 'MEDIUM'

        current_atr = atr.iloc[-1]
        current_price = df['close'].iloc[-1]

        if current_price <= 0:
            return 'MEDIUM'

        ratio = current_atr / current_price

        if ratio < 0.003:
            return 'LOW'
        elif ratio < 0.008:
            return 'MEDIUM'
        else:
            return 'HIGH'

    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Add all indicators to the dataframe."""
        result = df.copy()
        result['rsi'] = TechnicalIndicators.calculate_rsi(df)
        result['atr'] = TechnicalIndicators.calculate_atr(df)
        result['ema_5'] = TechnicalIndicators.calculate_ema(df, 5)
        result['ema_20'] = TechnicalIndicators.calculate_ema(df, 20)
        result['ema_50'] = TechnicalIndicators.calculate_ema(df, 50)
        result['ema_200'] = TechnicalIndicators.calculate_ema(df, 200)
        return result


def _deduplicate_levels(levels: List[float], tolerance: float = 1.0) -> List[float]:
    """Remove levels that are within tolerance of each other, keeping the average."""
    if not levels:
        return []

    levels_sorted = sorted(levels)
    result = []
    group = [levels_sorted[0]]

    for i in range(1, len(levels_sorted)):
        if levels_sorted[i] - group[-1] <= tolerance:
            group.append(levels_sorted[i])
        else:
            result.append(float(np.mean(group)))
            group = [levels_sorted[i]]

    if group:
        result.append(float(np.mean(group)))

    return result
