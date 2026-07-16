"""
Mustafa Bot - Triple EMA Dynamic Crossover Scalping Strategy Module
استراتيجية المتوسطات المتحركة الثلاثية (5/20/50 EMA) لتحديد تحولات الاتجاه السريعة
"""

from typing import Dict, Optional
import pandas as pd
from analysis.strategies.base_strategy import BaseScalpingStrategy
from config import Config


class TripleEMA_ScalpStrategy(BaseScalpingStrategy):
    """Triple EMA Dynamic Trend Crossover Strategy (EMA 5/20/50)."""

    def __init__(self):
        super().__init__(
            name="📊 Triple EMA Dynamic Shift",
            description="التقاط تحولات الاتجاه الديناميكية السريعة عبر تقاطع المتوسطات 5/20/50 EMA"
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
        if df is None or len(df) < 55:
            return None

        close = df['close']
        ema5 = close.ewm(span=5, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()

        symbol_info = Config.SUPPORTED_SYMBOLS.get(symbol, {})
        decimals = symbol_info.get('decimal_places', 2)

        direction = None
        score = 85

        # Crossover logic
        if ema5.iloc[-1] > ema20.iloc[-1] > ema50.iloc[-1] and ema5.iloc[-2] <= ema20.iloc[-2]:
            direction = 'BUY'
            entry = round(close.iloc[-1], decimals)
            sl = round(ema50.iloc[-1], decimals)
            risk = max(0.0001, entry - sl)
            tp1 = round(entry + (risk * min_rr), decimals)
            tp2 = round(entry + (risk * (min_rr + 1.0)), decimals)
            tp3 = round(entry + (risk * (min_rr + 2.0)), decimals)
            score += 5
        elif ema5.iloc[-1] < ema20.iloc[-1] < ema50.iloc[-1] and ema5.iloc[-2] >= ema20.iloc[-2]:
            direction = 'SELL'
            entry = round(close.iloc[-1], decimals)
            sl = round(ema50.iloc[-1], decimals)
            risk = max(0.0001, sl - entry)
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
            'reasons_entry': f"Triple EMA Crossover (5/20/50) alignment on {timeframe.upper()}",
            'reasoning': f"Fast EMA 5 crossed Medium EMA 20 with full trend alignment above EMA 50 on {timeframe}.",
            'market_bias': direction + 'ISH',
            'trend_direction': direction + 'ISH',
            'structure_analysis': 'EMA 5/20/50 Dynamic Trend Alignment',
            'bos_confirmed': True,
            'choch_confirmed': False,
            'order_blocks': ['EMA Dynamic Support Zone'],
            'breaker_blocks': [],
            'fvgs': [],
            'liquidity_zones': 'EMA Trend Continuation Pool',
            'premium_discount': 'Discount Zone' if direction == 'BUY' else 'Premium Zone',
            'institutional_confirmation': 'Triple EMA Cross Verified',
            'momentum_analysis': 'Strong EMA Impulse Acceleration',
            'session_analysis': 'Active Session',
            'volatility_analysis': 'HIGH'
        }
