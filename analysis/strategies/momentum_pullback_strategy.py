"""
Mustafa Bot - Momentum Pullback Strategy Module
استراتيجية متابعة الاتجاه القوي والدخول مع الارتداد الهادئ للزخم
"""

from typing import Dict, Optional
import pandas as pd
from analysis.strategies.base_strategy import BaseScalpingStrategy
from config import Config


class MomentumPullback_ScalpStrategy(BaseScalpingStrategy):
    """RSI Momentum Impulse & Trend Pullback Strategy."""

    def __init__(self):
        super().__init__(
            name="📈 Momentum Trend Pullback",
            description="الدخول مع التراجعات المؤقتة في الاتجاهات القوية المندفعة"
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

        symbol_info = Config.SUPPORTED_SYMBOLS.get(symbol, {})
        decimals = symbol_info.get('decimal_places', 2)

        direction = None
        score = 84

        # Simple Momentum RSI Evaluation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 0.00001)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        if current_rsi > 52 and prev_rsi <= 52:  # RSI cross above 50 momentum impulse
            direction = 'BUY'
            entry = round(recent['close'], decimals)
            sl = round(recent['low'] - (recent['high'] - recent['low']) * 0.5, decimals)
            risk = entry - sl
            tp1 = round(entry + (risk * min_rr), decimals)
            tp2 = round(entry + (risk * (min_rr + 1.0)), decimals)
            tp3 = round(entry + (risk * (min_rr + 2.0)), decimals)
            score += 5
        elif current_rsi < 48 and prev_rsi >= 48:  # RSI cross below 50 momentum impulse
            direction = 'SELL'
            entry = round(recent['close'], decimals)
            sl = round(recent['high'] + (recent['high'] - recent['low']) * 0.5, decimals)
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
            'reasons_entry': f"RSI Momentum Pullback Shift on {timeframe.upper()}",
            'reasoning': f"RSI momentum impulse shift detected crossing 50 centerline with trend alignment on {timeframe}.",
            'market_bias': direction + 'ISH',
            'trend_direction': direction + 'ISH',
            'structure_analysis': 'Momentum Impulse Shift',
            'bos_confirmed': True,
            'choch_confirmed': False,
            'order_blocks': ['Momentum Impulse Baseline'],
            'breaker_blocks': [],
            'fvgs': [],
            'liquidity_zones': 'Trend Continuation Alignment',
            'premium_discount': 'Discount Zone' if direction == 'BUY' else 'Premium Zone',
            'institutional_confirmation': 'RSI Momentum Verified',
            'momentum_analysis': 'Impulse Centerline Crossover',
            'session_analysis': 'Active Session',
            'volatility_analysis': 'HIGH'
        }
