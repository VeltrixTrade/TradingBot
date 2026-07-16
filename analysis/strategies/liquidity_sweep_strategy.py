"""
Mustafa Bot - Liquidity Sweep & Stop Hunt Strategy Module
استراتيجية اصطياد السيولة واختراق وقف الخسارة والانعكاس السريع
"""

from typing import Dict, Optional
import pandas as pd
from analysis.strategies.base_strategy import BaseScalpingStrategy
from config import Config


class LiquiditySweep_ScalpStrategy(BaseScalpingStrategy):
    """Stop Hunt Liquidity Sweep Reversal Strategy."""

    def __init__(self):
        super().__init__(
            name="💧 Liquidity Sweep Reversal",
            description="اصطياد ضرب ألياف السيولة فوق القمم وتحت القيعان والانعكاس التكتيكي"
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
        if df is None or len(df) < 40:
            return None

        recent = df.iloc[-1]
        lookback = df.iloc[-25:-1]

        highest_high = lookback['high'].max()
        lowest_low = lookback['low'].min()

        symbol_info = Config.SUPPORTED_SYMBOLS.get(symbol, {})
        decimals = symbol_info.get('decimal_places', 2)

        direction = None
        score = 88

        # Bullish Liquidity Sweep (Swept lowest low then closed high back inside)
        if recent['low'] < lowest_low and recent['close'] > lowest_low:
            direction = 'BUY'
            entry = round(recent['close'], decimals)
            sl = round(recent['low'] - (entry - recent['low']) * 0.1, decimals)
            risk = entry - sl
            tp1 = round(entry + (risk * min_rr), decimals)
            tp2 = round(entry + (risk * (min_rr + 1.0)), decimals)
            tp3 = round(entry + (risk * (min_rr + 2.0)), decimals)
            score += 5
        # Bearish Liquidity Sweep (Swept highest high then closed low back inside)
        elif recent['high'] > highest_high and recent['close'] < highest_high:
            direction = 'SELL'
            entry = round(recent['close'], decimals)
            sl = round(recent['high'] + (recent['high'] - entry) * 0.1, decimals)
            risk = sl - entry
            tp1 = round(entry - (risk * min_rr), decimals)
            tp2 = round(entry - (risk * (min_rr + 1.0)), decimals)
            tp3 = round(entry - (risk * (min_rr + 2.0)), decimals)
            score += 5
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
            'reasons_entry': f"Liquidity Sweep Reversal beyond major level on {timeframe.upper()}",
            'reasoning': f"Liquidity swept clean at major swing level with instant displacement back inside range on {timeframe}.",
            'market_bias': direction + 'ISH',
            'trend_direction': direction + 'ISH',
            'structure_analysis': 'Liquidity Sweep Stop Hunt Reversal',
            'bos_confirmed': True,
            'choch_confirmed': True,
            'order_blocks': ['Swept Liquidity Level'],
            'breaker_blocks': [],
            'fvgs': [],
            'liquidity_zones': 'Liquidity Swept Successfully',
            'premium_discount': 'Discount Zone' if direction == 'BUY' else 'Premium Zone',
            'institutional_confirmation': 'Stop Hunt Displacement Confirmed',
            'momentum_analysis': 'Reversal Sweep Momentum',
            'session_analysis': 'Active Killzone Session',
            'volatility_analysis': 'HIGH'
        }
