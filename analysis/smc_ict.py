"""
Mustafa Bot - SMC/ICT Engine
المحرك الرئيسي الذي يجمع جميع مكونات التحليل
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from analysis.market_structure import MarketStructureAnalyzer
from analysis.order_blocks import OrderBlockDetector
from analysis.fair_value_gaps import FairValueGapDetector
from analysis.liquidity import LiquidityAnalyzer
from analysis.indicators import TechnicalIndicators

logger = logging.getLogger('mustafa_bot.analysis.engine')


class SMCICTEngine:
    """Main SMC/ICT analysis engine combining all components."""

    def __init__(self):
        self.market_structure = MarketStructureAnalyzer(swing_length=10)
        self.order_blocks = OrderBlockDetector(strength_threshold=5)
        self.fvg = FairValueGapDetector()
        self.liquidity = LiquidityAnalyzer(equal_level_tolerance=0.5)
        self.indicators = TechnicalIndicators()

    def analyze(self, df: pd.DataFrame, timeframe: str = 'M15') -> Dict:
        """Run complete SMC/ICT analysis."""
        if df is None or df.empty or len(df) < 30:
            logger.warning('Insufficient data for analysis')
            return self._empty_analysis()

        try:
            # 1. Market Structure
            ms = self.market_structure.analyze(df)

            # 2. Order Blocks
            active_obs = self.order_blocks.get_active_order_blocks(df, ms['bos_list'])

            # 3. Fair Value Gaps
            unfilled_fvgs = self.fvg.get_unfilled_fvgs(df)

            # 4. Liquidity
            liq = self.liquidity.get_liquidity_pools(
                df, ms['swing_highs'], ms['swing_lows']
            )

            # 5. Indicators
            df_ind = self.indicators.add_all_indicators(df)
            rsi = float(df_ind['rsi'].iloc[-1]) if not pd.isna(df_ind['rsi'].iloc[-1]) else 50.0
            atr = float(df_ind['atr'].iloc[-1]) if not pd.isna(df_ind['atr'].iloc[-1]) else 0.0
            ema_20 = float(df_ind['ema_20'].iloc[-1]) if not pd.isna(df_ind['ema_20'].iloc[-1]) else 0.0
            ema_50 = float(df_ind['ema_50'].iloc[-1]) if not pd.isna(df_ind['ema_50'].iloc[-1]) else 0.0
            ema_200 = float(df_ind['ema_200'].iloc[-1]) if not pd.isna(df_ind['ema_200'].iloc[-1]) else 0.0
            volatility = self.indicators.get_market_volatility(df)
            vol_profile = self.indicators.calculate_volume_profile(df)
            sr = self.indicators.calculate_support_resistance(df)

            # 6. Premium/Discount
            current_price = float(df['close'].iloc[-1])
            premium_discount = self._determine_premium_discount(
                df, ms['last_swing_high'], ms['last_swing_low']
            )

            # 7. Overall Bias
            overall_bias = self._determine_overall_bias(ms, rsi, ema_20, ema_50, current_price)

            # Compile analysis
            analysis = {
                'market_structure': {
                    'trend': ms['trend'],
                    'bos_list': ms['bos_list'][-5:],  # Last 5
                    'choch_list': ms['choch_list'][-3:],
                    'last_swing_high': ms['last_swing_high'],
                    'last_swing_low': ms['last_swing_low'],
                    'swing_highs_values': ms['swing_highs_values'][-10:],
                    'swing_lows_values': ms['swing_lows_values'][-10:],
                    'structure_strength': ms['structure_strength'],
                },
                'order_blocks': active_obs[:5],  # Top 5 by strength
                'fair_value_gaps': unfilled_fvgs[:5],  # Latest 5
                'liquidity': liq,
                'indicators': {
                    'rsi': rsi,
                    'atr': atr,
                    'ema_20': ema_20,
                    'ema_50': ema_50,
                    'ema_200': ema_200,
                    'volatility': volatility,
                    'volume_profile': vol_profile,
                    'support_resistance': sr,
                },
                'premium_discount': premium_discount,
                'overall_bias': overall_bias,
                'current_price': current_price,
                'timeframe': timeframe,
                'score': 0,
                'key_levels': [],
                'setups': [],
                'summary': '',
            }

            # 8. Key Levels
            analysis['key_levels'] = self._extract_key_levels(analysis)

            # 9. Score
            analysis['score'] = self._calculate_overall_score(analysis)

            # 10. Find Setups
            analysis['setups'] = self._find_setups(analysis, df)

            # 11. Summary
            analysis['summary'] = self.generate_analysis_summary(analysis)

            logger.info(f'Analysis complete: {timeframe} | Bias: {overall_bias} | Score: {analysis["score"]} | Setups: {len(analysis["setups"])}')

            return analysis

        except Exception as e:
            logger.error(f'Analysis error: {e}', exc_info=True)
            return self._empty_analysis()

    def _determine_premium_discount(self, df: pd.DataFrame,
                                      swing_high: Optional[float],
                                      swing_low: Optional[float]) -> str:
        """Determine if price is in premium or discount zone."""
        if swing_high is None or swing_low is None:
            return 'EQUILIBRIUM'

        current_price = float(df['close'].iloc[-1])
        mid_point = (swing_high + swing_low) / 2.0

        if current_price > mid_point + (swing_high - mid_point) * 0.2:
            return 'PREMIUM'
        elif current_price < mid_point - (mid_point - swing_low) * 0.2:
            return 'DISCOUNT'
        else:
            return 'EQUILIBRIUM'

    def _determine_overall_bias(self, ms: Dict, rsi: float,
                                  ema_20: float, ema_50: float,
                                  current_price: float) -> str:
        """Determine overall market bias."""
        bullish_points = 0
        bearish_points = 0

        # Market structure
        if ms['trend'] == 'BULLISH':
            bullish_points += 3
        elif ms['trend'] == 'BEARISH':
            bearish_points += 3

        # Recent BOS
        if ms['bos_list']:
            last_bos = ms['bos_list'][-1]
            if last_bos['type'] == 'BULLISH':
                bullish_points += 2
            else:
                bearish_points += 2

        # RSI
        if rsi > 60:
            bullish_points += 1
        elif rsi < 40:
            bearish_points += 1

        # EMA alignment
        if current_price > ema_20 > ema_50:
            bullish_points += 2
        elif current_price < ema_20 < ema_50:
            bearish_points += 2

        if bullish_points > bearish_points + 1:
            return 'BULLISH'
        elif bearish_points > bullish_points + 1:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def _calculate_overall_score(self, analysis: Dict) -> int:
        """Calculate overall setup quality score 0-100."""
        score = 0

        # Market structure clarity (0-25)
        structure_strength = analysis['market_structure']['structure_strength']
        score += int(structure_strength * 0.25)

        # Order block quality (0-25)
        obs = analysis['order_blocks']
        if obs:
            best_ob_strength = max(ob['strength'] for ob in obs)
            score += int(best_ob_strength * 2.5)

        # FVG presence (0-15)
        fvgs = analysis['fair_value_gaps']
        if fvgs:
            score += min(15, len(fvgs) * 5)

        # Liquidity setup (0-15)
        sweeps = analysis['liquidity'].get('sweeps', [])
        if sweeps:
            reversal_sweeps = [s for s in sweeps if s.get('reversal', False)]
            score += min(15, len(reversal_sweeps) * 8 + len(sweeps) * 3)

        # Indicator confluence (0-20)
        rsi = analysis['indicators']['rsi']
        bias = analysis['overall_bias']
        if bias == 'BULLISH' and 30 < rsi < 70:
            score += 10
        elif bias == 'BEARISH' and 30 < rsi < 70:
            score += 10
        if analysis['indicators']['volatility'] in ('MEDIUM', 'HIGH'):
            score += 5
        if analysis['premium_discount'] in ('DISCOUNT', 'PREMIUM'):
            score += 5

        return min(100, max(0, score))

    def _extract_key_levels(self, analysis: Dict) -> List[float]:
        """Extract important price levels from the analysis."""
        levels = set()

        # Swing highs/lows
        sh = analysis['market_structure'].get('last_swing_high')
        sl = analysis['market_structure'].get('last_swing_low')
        if sh:
            levels.add(round(sh, 2))
        if sl:
            levels.add(round(sl, 2))

        # Order block edges
        for ob in analysis['order_blocks'][:3]:
            levels.add(round(ob['top'], 2))
            levels.add(round(ob['bottom'], 2))

        # FVG edges
        for fvg in analysis['fair_value_gaps'][:3]:
            levels.add(round(fvg['top'], 2))
            levels.add(round(fvg['bottom'], 2))

        # Liquidity levels
        for liq in analysis['liquidity'].get('buy_side', [])[:2]:
            levels.add(round(liq['level'], 2))
        for liq in analysis['liquidity'].get('sell_side', [])[:2]:
            levels.add(round(liq['level'], 2))

        # S/R levels
        for s in analysis['indicators']['support_resistance'].get('support_levels', [])[:3]:
            levels.add(round(s, 2))
        for r in analysis['indicators']['support_resistance'].get('resistance_levels', [])[:3]:
            levels.add(round(r, 2))

        return sorted(levels)

    def _find_setups(self, analysis: Dict, df: pd.DataFrame) -> List[Dict]:
        """Find trade setups where SMC confluences align."""
        setups = []
        current_price = analysis['current_price']
        atr = analysis['indicators']['atr']
        bias = analysis['overall_bias']

        if atr <= 0:
            atr = 5.0  # Default ATR for gold

        # Check each order block for confluence with FVGs and liquidity
        for ob in analysis['order_blocks']:
            confluence_list = [f"Order Block ({ob['type']})"]
            confluence_count = 1

            # Check FVG confluence
            for fvg in analysis['fair_value_gaps']:
                if (fvg['type'] == ob['type'] and
                    abs(fvg['bottom'] - ob['bottom']) < atr * 2):
                    confluence_list.append(f"FVG ({fvg['type']})")
                    confluence_count += 1
                    break

            # Check liquidity confluence
            sweeps = analysis['liquidity'].get('sweeps', [])
            for sweep in sweeps:
                if sweep.get('reversal', False):
                    confluence_list.append('Liquidity Sweep + Reversal')
                    confluence_count += 1
                    break

            # Check market structure confluence
            if analysis['market_structure']['trend'] != 'RANGING':
                if (ob['type'] == 'BULLISH' and analysis['market_structure']['trend'] == 'BULLISH') or \
                   (ob['type'] == 'BEARISH' and analysis['market_structure']['trend'] == 'BEARISH'):
                    confluence_list.append(f"Trend Alignment ({analysis['market_structure']['trend']})")
                    confluence_count += 1

            # Check premium/discount confluence
            pd_zone = analysis['premium_discount']
            if (ob['type'] == 'BULLISH' and pd_zone == 'DISCOUNT') or \
               (ob['type'] == 'BEARISH' and pd_zone == 'PREMIUM'):
                confluence_list.append(f"Zone ({pd_zone})")
                confluence_count += 1

            if confluence_count >= 2:
                direction = 'BUY' if ob['type'] == 'BULLISH' else 'SELL'

                if direction == 'BUY':
                    entry = ob['top']
                    stop_loss = ob['bottom'] - atr * 0.5
                    tp1 = entry + (entry - stop_loss) * 2
                    tp2 = entry + (entry - stop_loss) * 3
                    tp3 = entry + (entry - stop_loss) * 5
                else:
                    entry = ob['bottom']
                    stop_loss = ob['top'] + atr * 0.5
                    tp1 = entry - (stop_loss - entry) * 2
                    tp2 = entry - (stop_loss - entry) * 3
                    tp3 = entry - (stop_loss - entry) * 5

                setup_score = min(100, ob['strength'] * 8 + confluence_count * 10)

                # Arabic description
                direction_ar = 'شراء' if direction == 'BUY' else 'بيع'
                confluences_text = ' + '.join(confluence_list)

                description = (
                    f"إعداد {direction_ar} عند أوردر بلوك "
                    f"بين {ob['bottom']:.2f} و {ob['top']:.2f} "
                    f"مع {confluence_count} تقاطعات: {confluences_text}"
                )

                setups.append({
                    'direction': direction,
                    'entry_zone': (ob['bottom'], ob['top']),
                    'entry': round(entry, 2),
                    'stop_loss': round(stop_loss, 2),
                    'tp1': round(tp1, 2),
                    'tp2': round(tp2, 2),
                    'tp3': round(tp3, 2),
                    'confluence_count': confluence_count,
                    'confluence_list': confluence_list,
                    'description': description,
                    'score': setup_score,
                    'ob_strength': ob['strength'],
                })

        # Sort by score descending
        setups.sort(key=lambda x: x['score'], reverse=True)
        return setups[:5]  # Top 5 setups

    def multi_timeframe_analysis(self, dataframes: Dict[str, pd.DataFrame]) -> Dict:
        """Run analysis on multiple timeframes and combine."""
        analyses = {}
        higher_tf_bias = 'NEUTRAL'

        # Analyze from highest to lowest timeframe
        tf_order = ['1d', '4h', '1h', '15m', '5m']
        available_tfs = [tf for tf in tf_order if tf in dataframes]

        for tf in available_tfs:
            analysis = self.analyze(dataframes[tf], tf)
            analyses[tf] = analysis

            # Higher timeframe sets the bias
            if tf in ('1d', '4h'):
                if analysis['overall_bias'] != 'NEUTRAL':
                    higher_tf_bias = analysis['overall_bias']

        # Filter lower TF setups by higher TF bias
        for tf in ('15m', '5m'):
            if tf in analyses and higher_tf_bias != 'NEUTRAL':
                filtered_setups = [
                    s for s in analyses[tf]['setups']
                    if s['direction'] == higher_tf_bias or higher_tf_bias == 'NEUTRAL'
                ]
                analyses[tf]['setups'] = filtered_setups

        return {
            'analyses': analyses,
            'higher_tf_bias': higher_tf_bias,
            'available_timeframes': available_tfs,
            'best_timeframe': available_tfs[-1] if available_tfs else 'M15',
        }

    def generate_analysis_summary(self, analysis: Dict) -> str:
        """Generate a human-readable summary in Arabic."""
        trend_map = {'BULLISH': 'صاعد 📈', 'BEARISH': 'هابط 📉', 'NEUTRAL': 'محايد ↔️', 'RANGING': 'عرضي ↔️'}
        pd_map = {'PREMIUM': 'منطقة بريميوم (بيع)', 'DISCOUNT': 'منطقة ديسكاونت (شراء)', 'EQUILIBRIUM': 'منطقة التوازن'}

        trend = trend_map.get(analysis['overall_bias'], 'محايد')
        pd_zone = pd_map.get(analysis['premium_discount'], 'غير محدد')

        summary = f"""📊 تحليل الذهب | {analysis['timeframe']}

🔹 الاتجاه العام: {trend}
🔹 قوة الهيكل: {analysis['market_structure']['structure_strength']}%
🔹 المنطقة: {pd_zone}
🔹 السعر الحالي: {analysis['current_price']:.2f}

📐 المؤشرات:
  • RSI: {analysis['indicators']['rsi']:.1f}
  • ATR: {analysis['indicators']['atr']:.2f}
  • EMA20: {analysis['indicators']['ema_20']:.2f}
  • EMA50: {analysis['indicators']['ema_50']:.2f}
  • التقلب: {analysis['indicators']['volatility']}

🏛️ أوردر بلوكات نشطة: {len(analysis['order_blocks'])}
📊 فجوات قيمة عادلة: {len(analysis['fair_value_gaps'])}
💧 مناطق سيولة: {len(analysis['liquidity'].get('buy_side', [])) + len(analysis['liquidity'].get('sell_side', []))}

⚡ جودة الإعداد: {analysis['score']}/100
🎯 إعدادات متاحة: {len(analysis['setups'])}"""

        return summary

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure."""
        return {
            'market_structure': {
                'trend': 'NEUTRAL', 'bos_list': [], 'choch_list': [],
                'last_swing_high': None, 'last_swing_low': None,
                'swing_highs_values': [], 'swing_lows_values': [],
                'structure_strength': 0,
            },
            'order_blocks': [],
            'fair_value_gaps': [],
            'liquidity': {'buy_side': [], 'sell_side': [], 'all_levels': [], 'sweeps': [], 'current_price': 0},
            'indicators': {
                'rsi': 50, 'atr': 0, 'ema_20': 0, 'ema_50': 0, 'ema_200': 0,
                'volatility': 'LOW', 'volume_profile': {}, 'support_resistance': {},
            },
            'premium_discount': 'EQUILIBRIUM',
            'overall_bias': 'NEUTRAL',
            'current_price': 0,
            'timeframe': '',
            'score': 0,
            'key_levels': [],
            'setups': [],
            'summary': 'لا توجد بيانات كافية للتحليل',
        }
