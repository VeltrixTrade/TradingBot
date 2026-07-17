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
from analysis.triple_ema import TripleEMACrossover

logger = logging.getLogger('mustafa_bot.analysis.engine')


class SMCICTEngine:
    """Main SMC/ICT analysis engine combining all components."""

    def __init__(self):
        self.market_structure = MarketStructureAnalyzer(swing_length=10)
        self.order_blocks = OrderBlockDetector(strength_threshold=5)
        self.fvg = FairValueGapDetector()
        self.liquidity = LiquidityAnalyzer(equal_level_tolerance=0.5)
        self.indicators = TechnicalIndicators()
        self.triple_ema = TripleEMACrossover(fast=5, medium=20, slow=50)

    def analyze(self, df: pd.DataFrame, timeframe: str = 'M15', symbol_key: str = 'XAU/USD') -> Dict:
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

            # 5.5 Triple EMA Crossover Analysis
            triple_ema_result = self.triple_ema.analyze(df)

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
                'triple_ema': triple_ema_result,
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
            analysis['setups'] = self._find_setups(analysis, df, symbol_key=symbol_key)

            # 11. Summary
            analysis['summary'] = self.generate_analysis_summary(analysis)

            logger.info(f'Analysis complete: {symbol_key} ({timeframe}) | Bias: {overall_bias} | Score: {analysis["score"]} | Setups: {len(analysis["setups"])}')

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

    def _find_setups(self, analysis: Dict, df: pd.DataFrame, symbol_key: str = 'XAU/USD') -> List[Dict]:
        """Find trade setups where SMC confluences align."""
        from config import Config
        sym_info = Config.SUPPORTED_SYMBOLS.get(symbol_key, {})
        decimals = sym_info.get('decimal_places', 2)

        setups = []
        current_price = analysis['current_price']
        atr = analysis['indicators']['atr']
        bias = analysis['overall_bias']

        if atr <= 0:
            atr = current_price * 0.002

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

            if confluence_count >= 1:
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

                # ─── Triple EMA Confirmation Layer ───
                triple_ema = analysis.get('triple_ema', {})
                ema_confirmed, ema_reason = self.triple_ema.confirms_direction(triple_ema, direction)
                ema_boost = triple_ema.get('confidence_boost', 0)

                if ema_confirmed:
                    confluence_list.append(f'Triple EMA ({ema_reason})')
                    confluence_count += 1
                    setup_score = min(100, setup_score + ema_boost)
                else:
                    setup_score = max(30, setup_score - 10)
                    confluence_list.append(f'Triple EMA ({ema_reason})')

                # Arabic description
                direction_ar = 'شراء' if direction == 'BUY' else 'بيع'
                confluences_text = ' + '.join(confluence_list)

                description = (
                    f"إعداد {direction_ar} عند أوردر بلوك "
                    f"بين {ob['bottom']:.{decimals}f} و {ob['top']:.{decimals}f} "
                    f"مع {confluence_count} تقاطعات: {confluences_text}"
                )

                setups.append({
                    'symbol': symbol_key,
                    'direction': direction,
                    'entry_zone': (round(ob['bottom'], decimals), round(ob['top'], decimals)),
                    'entry': round(entry, decimals),
                    'stop_loss': round(stop_loss, decimals),
                    'tp1': round(tp1, decimals),
                    'tp2': round(tp2, decimals),
                    'tp3': round(tp3, decimals),
                    'confluence_count': confluence_count,
                    'confluence_list': confluence_list,
                    'description': description,
                    'score': setup_score,
                    'ob_strength': ob['strength'],
                    'ema_confirmed': ema_confirmed,
                    'ema_reason': ema_reason,
                })

        if not setups:
            # Fallback setup based on Triple EMA + indicators/trend
            triple_ema = analysis.get('triple_ema', {})
            ema_direction = triple_ema.get('crossover_direction')
            ema_trend = triple_ema.get('trend', 'NEUTRAL')

            # Priority: Triple EMA direction > bias > RSI
            if ema_direction:
                direction = ema_direction
            elif ema_trend == 'BULLISH':
                direction = 'BUY'
            elif ema_trend == 'BEARISH':
                direction = 'SELL'
            elif bias == 'BULLISH':
                direction = 'BUY'
            elif bias == 'BEARISH':
                direction = 'SELL'
            else:
                direction = 'BUY' if analysis['indicators']['rsi'] < 50 else 'SELL'

            entry = current_price
            if direction == 'BUY':
                stop_loss = current_price - atr * 1.5
                tp1 = current_price + atr * 2.0
                tp2 = current_price + atr * 3.5
                tp3 = current_price + atr * 5.0
            else:
                stop_loss = current_price + atr * 1.5
                tp1 = current_price - atr * 2.0
                tp2 = current_price - atr * 3.5
                tp3 = current_price - atr * 5.0

            ema_confirmed, ema_reason = self.triple_ema.confirms_direction(triple_ema, direction)
            ema_boost = triple_ema.get('confidence_boost', 0)
            fallback_score = 70 + ema_boost if ema_confirmed else 60

            confluence_list = ['Technical Fallback (Trend/RSI)']
            if ema_confirmed:
                confluence_list.append(f'Triple EMA ({ema_reason})')

            direction_emoji = '🟢' if direction == 'BUY' else '🔴'
            description = f"إعداد {('شراء' if direction == 'BUY' else 'بيع')} {direction_emoji} احتياطي فني بناءً على Triple EMA + الاتجاه {bias} | السعر: {current_price:.2f}"
            setups.append({
                'direction': direction,
                'entry_zone': (entry - atr*0.2, entry + atr*0.2),
                'entry': round(entry, 2),
                'stop_loss': round(stop_loss, 2),
                'tp1': round(tp1, 2),
                'tp2': round(tp2, 2),
                'tp3': round(tp3, 2),
                'confluence_count': len(confluence_list),
                'confluence_list': confluence_list,
                'description': description,
                'score': fallback_score,
                'ob_strength': 5,
                'ema_confirmed': ema_confirmed,
                'ema_reason': ema_reason,
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
        """Generate a highly detailed and visually premium summary in Arabic."""
        def make_progress_bar(percentage: int, total_chars: int = 10, fill_char: str = '🟩', empty_char: str = '⬜') -> str:
            filled = int(round((percentage / 100) * total_chars))
            filled = min(total_chars, max(0, filled))
            return (fill_char * filled) + (empty_char * (total_chars - filled))

        def make_rsi_bar(rsi_val: float) -> str:
            idx = int(rsi_val / 10)
            idx = min(9, max(0, idx))
            bar = ['⬜'] * 10
            for i in range(10):
                if i == idx:
                    bar[i] = '🔷'
                elif i < 3:
                    bar[i] = '🟥'
                elif i >= 7:
                    bar[i] = '🟥'
                else:
                    bar[i] = '🟩'
            return "".join(bar)

        def make_pd_bar(zone: str) -> str:
            if zone == 'PREMIUM':
                return '🔴 بريميوم (مناسب للبيع) [ 🟥 ⬤ | ⬜ | ⬜ ]'
            elif zone == 'DISCOUNT':
                return '🟢 ديسكاونت (مناسب للشراء) [ ⬜ | ⬜ | 🟩 ⬤ ]'
            else:
                return '🟡 منطقة التوازن (حيادي) [ ⬜ | 🟨 ⬤ | ⬜ ]'

        # Sessions
        from datetime import datetime, timezone
        current_hour_utc = datetime.now(timezone.utc).hour
        active_sessions = []
        if 8 <= current_hour_utc < 16:
            active_sessions.append("لندن 🇬🇧")
        if 13 <= current_hour_utc < 21:
            active_sessions.append("نيويورك 🇺🇸")
        if 0 <= current_hour_utc < 8:
            active_sessions.append("طوكيو/سيدني 🇯🇵")
        session_text = " + ".join(active_sessions) if active_sessions else "فترة انتقالية هادئة 💤"

        trend_map = {'BULLISH': 'صاعد 📈', 'BEARISH': 'هابط 📉', 'NEUTRAL': 'محايد ↔️', 'RANGING': 'عرضي ↔️'}
        trend = trend_map.get(analysis['overall_bias'], 'محايد')
        
        struct_strength = analysis['market_structure']['structure_strength']
        struct_bar = make_progress_bar(struct_strength, 10, '🟩', '⬜')
        
        pd_zone = analysis['premium_discount']
        pd_bar = make_pd_bar(pd_zone)
        
        rsi = analysis['indicators']['rsi']
        rsi_bar = make_rsi_bar(rsi)
        
        score = analysis['score']
        score_bar = make_progress_bar(score, 10, '🔥', '⬜')

        # Triple EMA
        triple_ema = analysis.get('triple_ema', {})
        ema_trend = triple_ema.get('trend', 'NEUTRAL')
        ema_trend_ar = 'صاعد 📈' if ema_trend == 'BULLISH' else 'هابط 📉' if ema_trend == 'BEARISH' else 'محايد ↔️'
        ema_align = triple_ema.get('alignment', 'NONE')
        
        align_ar = 'غير محدد'
        if ema_align == 'PERFECT_BULL':
            align_ar = '🟢 ترتيب صاعد مثالي (السعر فوق المتوسطات)'
        elif ema_align == 'PERFECT_BEAR':
            align_ar = '🔴 ترتيب هابط مثالي (السعر تحت المتوسطات)'
        elif ema_align == 'PARTIAL':
            align_ar = '🟡 ترتيب جزئي غير مكتمل'
        
        initial = triple_ema.get('initial_signal')
        confirmation = triple_ema.get('confirmation_signal')
        
        ema_signals = []
        if initial:
            ema_signals.append(initial['description_ar'])
        if confirmation:
            ema_signals.append(confirmation['description_ar'])
        ema_signals_text = "\n    • ".join(ema_signals) if ema_signals else "لا توجد تقاطعات حديثة"

        summary = f"""📊 تحليل هيكل السوق (SMC/ICT)
━━━━━━━━━━━━━━━━━━━━
⏰ الجلسة الحالية: {session_text}
🔹 الاتجاه العام: {trend}
🔹 قوة الهيكل: {struct_strength}%
  [{struct_bar}]
🔹 المنطقة السعرية: {pd_bar}
🔹 السعر الحالي للذهب: {analysis['current_price']:.2f}

📐 المؤشرات الفنية والسيولة:
  • زخم RSI: {rsi:.1f}
    [{rsi_bar}]
  • معدل التذبذب ATR: {analysis['indicators']['atr']:.2f}
  • التقلب: {analysis['indicators']['volatility']}
  • أوردر بلوكات نشطة: {len(analysis['order_blocks'])}
  • فجوات قيمة عادلة FVG: {len(analysis['fair_value_gaps'])}

📈 استراتيجية Triple EMA (5, 20, 50):
  • اتجاه المتوسطات: {ema_trend_ar}
  • توافق الترتيب: {align_ar}
  • حالة التقاطعات:
    • {ema_signals_text}

⚡ جودة الصفقة الإجمالية: {score}/100
  [{score_bar}]
🎯 صفقات التداول المتاحة: {len(analysis['setups'])}"""

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
            'triple_ema': {
                'trend': 'NEUTRAL', 'alignment': 'NONE',
                'initial_signal': None, 'confirmation_signal': None,
                'crossover_direction': None,
                'ema_values': {'ema_5': 0, 'ema_20': 0, 'ema_50': 0},
                'confidence_boost': 0,
                'description': 'لا توجد بيانات كافية لتحليل Triple EMA',
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

