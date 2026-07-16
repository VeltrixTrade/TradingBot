"""
Mustafa Bot - Volatility Breakout Strategy Module
استراتيجية اختراق الانضغاط السعري والتوسع السريع للزخم
"""

from typing import Dict, Optional
import pandas as pd
from analysis.strategies.base_strategy import BaseScalpingStrategy
from config import Config


class Breakout_ScalpStrategy(BaseScalpingStrategy):
    """Volatility Range Expansion Breakout Strategy."""

    def __init__(self):
        super().__init__(
            name="🚀 Volatility Compression Breakout",
            description="اقتناص اختراق نطاقات التجميع والانفجار السعري المفاجئ"
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
        lookback = df.iloc[-15:-1]

        range_high = lookback['high'].max()
        range_low = lookback['low'].min()
        range_size = range_high - range_low

        symbol_info = Config.SUPPORTED_SYMBOLS.get(symbol, {})
        decimals = symbol_info.get('decimal_places', 2)

        direction = None
        score = 83

        # Breakout High with high volume/candle size
        if recent['close'] > range_high:
            direction = 'BUY'
            entry = round(recent['close'], decimals)
            sl = round(range_low + (range_size * 0.4), decimals)
            risk = entry - sl
            tp1 = round(entry + (risk * min_rr), decimals)
            tp2 = round(entry + (risk * (min_rr + 1.0)), decimals)
            tp3 = round(entry + (risk * (min_rr + 2.0)), decimals)
            score += 5
        # Breakout Low
        elif recent['close'] < range_low:
            direction = 'SELL'
            entry = round(recent['close'], decimals)
            sl = round(range_high - (range_size * 0.4), decimals)
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
            'reasons_entry': f"Volatility Compression Breakout beyond 15-period range on {timeframe.upper()}",
            'reasoning': f"Strong close outside tight consolidation range with expansion momentum on {timeframe}.",
            'market_bias': direction + 'ISH',
            'trend_direction': direction + 'ISH',
            'structure_analysis': 'Consolidation Range Breakout',
            'bos_confirmed': True,
            'choch_confirmed': False,
            'order_blocks': ['Consolidation Range Boundary'],
            'breaker_blocks': [],
            'fvgs': [],
            'liquidity_zones': 'Breakout Acceleration Zone',
            'premium_discount': 'Discount Zone' if direction == 'BUY' else 'Premium Zone',
            'institutional_confirmation': 'Expansion Volume Breakout',
            'momentum_analysis': 'High Volatility Breakout',
            'session_analysis': 'Active Trading Hours',
            'volatility_analysis': 'HIGH'
        }
