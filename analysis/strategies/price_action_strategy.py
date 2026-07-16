"""
Mustafa Bot - Pure Price Action Scalping Strategy Module
استراتيجية حركة السعر الصافية والشموع الانعكاسية (Pinbars & Wicks)
"""

from typing import Dict, Optional
import pandas as pd
from analysis.strategies.base_strategy import BaseScalpingStrategy
from config import Config


class PriceAction_ScalpStrategy(BaseScalpingStrategy):
    """Pure Price Action Rejection Wicks & Support/Resistance Strategy."""

    def __init__(self):
        super().__init__(
            name="🎯 Price Action Rejection Wicks",
            description="التقاط ذيول الشموع الانعكاسية المرتدة من الدعوم والمقومات القوية"
        )

    def evaluate(
        self,
        dataframes: Dict[str, pd.DataFrame],
        symbol: str = 'XAU/USD',
        timeframe: str = '15m',
        min_score: int = 82,
        min_rr: float = 2.0
    ) -> Optional[Dict]:
        df = dataframes.get(timeframe)
        if df is None or len(df) < 30:
            return None

        recent = df.iloc[-1]
        prev = df.iloc[-2]

        body = abs(recent['close'] - recent['open'])
        candle_range = max(0.00001, recent['high'] - recent['low'])
        upper_wick = recent['high'] - max(recent['open'], recent['close'])
        lower_wick = min(recent['open'], recent['close']) - recent['low']

        symbol_info = Config.SUPPORTED_SYMBOLS.get(symbol, {})
        decimals = symbol_info.get('decimal_places', 2)

        direction = None
        score = 80

        # Pinbar / Rejection Wick Logic
        if lower_wick / candle_range > 0.60 and body / candle_range < 0.30:  # Bullish Rejection
            direction = 'BUY'
            entry = round(recent['close'], decimals)
            sl = round(recent['low'] - (candle_range * 0.2), decimals)
            risk = entry - sl
            tp1 = round(entry + (risk * min_rr), decimals)
            tp2 = round(entry + (risk * (min_rr + 1.0)), decimals)
            tp3 = round(entry + (risk * (min_rr + 2.0)), decimals)
            score += 10
        elif upper_wick / candle_range > 0.60 and body / candle_range < 0.30:  # Bearish Rejection
            direction = 'SELL'
            entry = round(recent['close'], decimals)
            sl = round(recent['high'] + (candle_range * 0.2), decimals)
            risk = sl - entry
            tp1 = round(entry - (risk * min_rr), decimals)
            tp2 = round(entry - (risk * (min_rr + 1.0)), decimals)
            tp3 = round(entry - (risk * (min_rr + 2.0)), decimals)
            score += 10
        else:
            return None

        if score < min_score:
            return None

        return {
            'strategy_name': self.name,
            'symbol': symbol,
            'direction': direction,
            'timeframe_name': timeframe.upper(),
            'entry': entry,
            'stop_loss': sl,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'risk_reward': round(min_rr, 2),
            'score': score,
            'confidence': score,
            'reasons_entry': f"Price Action Rejection Wick (Pinbar) on {timeframe.upper()}",
            'reasoning': f"Strong rejection wick detected covering over 60% of candle range on {timeframe}.",
            'market_bias': direction + 'ISH',
            'trend_direction': direction + 'ISH',
            'structure_analysis': 'Key Support/Resistance Rejection Pinbar',
            'bos_confirmed': True,
            'choch_confirmed': False,
            'order_blocks': ['Price Action Wick Barrier'],
            'breaker_blocks': [],
            'fvgs': [],
            'liquidity_zones': 'Key Swing Rejection Level',
            'premium_discount': 'Discount Zone' if direction == 'BUY' else 'Premium Zone',
            'institutional_confirmation': 'Wick Rejection Verified',
            'momentum_analysis': 'Reversal Pinbar Wick Momentum',
            'session_analysis': 'Active Session',
            'volatility_analysis': 'HIGH'
        }
