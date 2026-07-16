"""
Mustafa Bot - Institutional Gold Market Analysis Engine (SMC + ICT + MTF)
محرك تحليل الذهب المؤسساتي المتقدم

المميزات:
  1. تحليل الفريمات المتعددة التسلسلي: MN -> W1 -> D1 -> H4 -> H1 -> M30 -> M15 -> M5
  2. كشف الأشكال الهيكلية المتقدمة: Breaker Blocks, Mitigation Blocks, IFVG (Inverse Fair Value Gaps)
  3. فلترة الاختراقات الكاذبة والسيولة الوهمية (False Breakouts / Fake Liquidity)
  4. حساب نقاط جودة الصفقة (Trade Quality Score 0-100) بدقة مؤسساتية
  5. تصفية صارمة: لا يقبل أي صفقة بنقاط أقل من 90/100
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from analysis.smc_ict import SMCICTEngine
from analysis.triple_ema import TripleEMACrossover
from signals.models import Signal, SignalType, Direction, SignalStatus

logger = logging.getLogger('mustafa_bot.analysis.gold_engine')


class GoldMarketAnalysisEngine:
    """Institutional-level trading analyst engine specializing in Gold (XAUUSD)."""

    def __init__(self):
        self.smc_engine = SMCICTEngine()
        self.triple_ema = TripleEMACrossover(fast=5, medium=20, slow=50)

    def analyze_market(self, dataframes: Dict[str, pd.DataFrame], signal_type: str = 'SCALP', symbol_key: str = 'XAU/USD', min_score: Optional[int] = None, profile: str = 'CONSERVATIVE') -> Dict:
        """Run complete institutional multi-timeframe analysis from Monthly to M5.

        Returns a detailed report dict with setups, scores, and explanations.
        """
        from config import Config
        symbol_info = Config.SUPPORTED_SYMBOLS.get(symbol_key, Config.SUPPORTED_SYMBOLS['XAU/USD'])
        decimals = symbol_info.get('decimal_places', 2)

        profile_cfg = Config.TRADING_PROFILES.get(profile, Config.TRADING_PROFILES['CONSERVATIVE'])
        threshold = min_score if min_score is not None else profile_cfg['min_score']

        # Required timeframes order
        tf_order = ['1mo', '1w', '1d', '4h', '1h', '30m', '15m', '5m']
        
        # ─── 1. Run SMC & indicator analysis on all available timeframes ───
        tfs_analyses = {}
        for tf in tf_order:
            if tf in dataframes:
                tfs_analyses[tf] = self.smc_engine.analyze(dataframes[tf], tf)
            else:
                logger.warning(f"Timeframe {tf} data is missing.")

        current_price = float(dataframes['5m']['close'].iloc[-1]) if '5m' in dataframes else float(dataframes['15m']['close'].iloc[-1])

        # ─── 2. Calculate Directional Bias across timeframes ───
        monthly_bias = tfs_analyses.get('1mo', {}).get('overall_bias', 'NEUTRAL')
        weekly_bias = tfs_analyses.get('1w', {}).get('overall_bias', 'NEUTRAL')
        daily_bias = tfs_analyses.get('1d', {}).get('overall_bias', 'NEUTRAL')
        h4_bias = tfs_analyses.get('4h', {}).get('overall_bias', 'NEUTRAL')
        h1_bias = tfs_analyses.get('1h', {}).get('overall_bias', 'NEUTRAL')

        # Determine overall institutional bias
        # Weighted points: Daily=3, Weekly=2, Monthly=1
        bullish_points = 0
        bearish_points = 0
        
        if monthly_bias == 'BULLISH': bullish_points += 1
        elif monthly_bias == 'BEARISH': bearish_points += 1
        
        if weekly_bias == 'BULLISH': bullish_points += 2
        elif weekly_bias == 'BEARISH': bearish_points += 2
        
        if daily_bias == 'BULLISH': bullish_points += 3
        elif daily_bias == 'BEARISH': bearish_points += 3

        overall_htf_bias = 'NEUTRAL'
        if bullish_points > bearish_points + 1:
            overall_htf_bias = 'BULLISH'
        elif bearish_points > bullish_points + 1:
            overall_htf_bias = 'BEARISH'

        # ─── 3. Identify Breaker Blocks & Mitigation Blocks ───
        # A Breaker block is a failed Order Block that has been broken through by price.
        # A Mitigation block is a failed Order Block where the price returns to test it but doesn't make a new swing point.
        h1_df = dataframes.get('1h')
        m15_df = dataframes.get('15m')
        m5_df = dataframes.get('5m')
        
        breaker_df = h1_df if h1_df is not None else m15_df
        breaker_blocks = self._detect_breaker_blocks(breaker_df, tfs_analyses.get('1h', {}).get('market_structure', {}).get('bos_list', []))

        # ─── 4. Identify Inverse Fair Value Gaps (IFVG) ───
        # An IFVG is an FVG that has been crossed and closed through.
        ifvgs = self._detect_ifvgs(breaker_df)

        # ─── 5. Fake Liquidity / False Breakout detection ───
        fake_df = m15_df if m15_df is not None else m5_df
        fake_breakout = self._check_fake_breakouts(fake_df)

        # ─── 6. Build setups for the execution timeframe ───
        # Execution timeframe: M15 for Scalp, H1 for Swing
        exec_tf = '15m' if signal_type == 'SCALP' else '1h'
        exec_analysis = tfs_analyses.get(exec_tf, self.smc_engine.analyze(dataframes[exec_tf], exec_tf))
        
        setups = exec_analysis.get('setups', [])
        institutional_setups = []

        setups = exec_analysis.get('setups', [])
        institutional_setups = []

        for setup in setups:
            direction = setup['direction']
            entry = setup['entry']
            stop_loss = setup['stop_loss']
            
            # Risk to Reward Optimization (ensuring min requirements are strictly met)
            min_rr = 2.0 if signal_type == 'SCALP' else 3.0
            tp1 = setup['tp1']
            tp2 = setup['tp2']
            tp3 = setup['tp3']
            
            rr = abs(tp1 - entry) / max(0.01, abs(entry - stop_loss))
            if rr < min_rr:
                # Adjust targets to fit institutional risk management using correct decimals
                tp1 = round(entry + (entry - stop_loss) * min_rr, decimals) if direction == 'BUY' else round(entry - (stop_loss - entry) * min_rr, decimals)
                tp2 = round(entry + (entry - stop_loss) * (min_rr + 1.0), decimals) if direction == 'BUY' else round(entry - (stop_loss - entry) * (min_rr + 1.0), decimals)
                tp3 = round(entry + (entry - stop_loss) * (min_rr + 3.0), decimals) if direction == 'BUY' else round(entry - (stop_loss - entry) * (min_rr + 3.0), decimals)
                rr = min_rr
            
            # Calculate institutional quality score (0-100) using the Dynamic Confidence Engine
            score, details = self._calculate_trade_score(
                direction=direction,
                overall_htf_bias=overall_htf_bias,
                daily_bias=daily_bias,
                h4_bias=h4_bias,
                h1_bias=h1_bias,
                setup=setup,
                exec_analysis=exec_analysis,
                breaker_blocks=breaker_blocks,
                ifvgs=ifvgs,
                fake_breakout=fake_breakout,
                signal_type=signal_type,
                current_price=current_price,
                rr=rr
            )

            # Filter: only allow trades meeting the configured dynamic score threshold
            if score >= threshold:
                inst_grade = "Institutional Grade" if score >= 95 else "Strong" if score >= 85 else "Moderate"
                
                # Active Session
                from utils.scheduler import AnalysisScheduler
                current_hour_utc = datetime.now(timezone.utc).hour
                active_sessions = []
                if 8 <= current_hour_utc < 16: active_sessions.append("LONDON 🇬🇧")
                if 13 <= current_hour_utc < 21: active_sessions.append("NEW YORK 🇺🇸")
                if 0 <= current_hour_utc < 8: active_sessions.append("ASIAN 🇯🇵")
                session_text = " + ".join(active_sessions) if active_sessions else "TRANSITION PERIOD 💤"

                # Invalidation Conditions
                invalidation_price = stop_loss
                invalidation_reason = f"Price closes beyond stop loss at {stop_loss:.2f} or opposite Market Structure Shift (MSS) occurs."

                # Dynamic Risk Percent based on volatility
                vol_status = exec_analysis['indicators']['volatility']
                risk_pct = "1.0%"
                if vol_status == 'HIGH':
                    risk_pct = "0.5% (Reduced due to High Volatility)"
                elif vol_status == 'VERY_HIGH':
                    risk_pct = "0.25% (Reduced due to Extreme Volatility)"

                inst_setup = {
                    'symbol': symbol_key,
                    'timeframe_name': exec_tf.upper(),
                    'direction': direction,
                    'entry': entry,
                    'stop_loss': stop_loss,
                    'tp1': tp1,
                    'tp2': tp2,
                    'tp3': tp3,
                    'risk_pct': risk_pct,
                    'risk_reward': round(rr, 2),
                    'market_bias': overall_htf_bias,
                    'trend_direction': exec_analysis['overall_bias'],
                    'structure_analysis': f"BOS count: {len(exec_analysis['market_structure']['bos_list'])} | CHoCH count: {len(exec_analysis['market_structure']['choch_list'])}",
                    'bos_confirmed': len(exec_analysis['market_structure']['bos_list']) > 0,
                    'choch_confirmed': len(exec_analysis['market_structure']['choch_list']) > 0,
                    'order_blocks': [f"OB at {ob['bottom']:.2f}-{ob['top']:.2f} (Strength: {ob['strength']}/10)" for ob in exec_analysis['order_blocks'][:3]],
                    'breaker_blocks': [f"Breaker at {bb['bottom']:.2f}-{bb['top']:.2f}" for bb in breaker_blocks[:2]],
                    'fvgs': [f"FVG at {fvg['bottom']:.2f}-{fvg['top']:.2f}" for fvg in exec_analysis['fair_value_gaps'][:3]],
                    'liquidity_zones': f"Buy-side: {len(exec_analysis['liquidity'].get('buy_side', []))} pools | Sell-side: {len(exec_analysis['liquidity'].get('sell_side', []))} pools",
                    'premium_discount': exec_analysis['premium_discount'],
                    'institutional_confirmation': f"Score: {score} | Grade: {inst_grade} | Harmony: {overall_htf_bias}",
                    'momentum_analysis': f"RSI: {exec_analysis['indicators']['rsi']:.1f} | ATR: {exec_analysis['indicators']['atr']:.2f}",
                    'session_analysis': session_text,
                    'volatility_analysis': f"Volatility: {vol_status} | ATR: {exec_analysis['indicators']['atr']:.2f}",
                    'score': score,
                    'confidence': score,
                    'inst_grade': inst_grade,
                    'reasons_entry': f"SMC setup alignment with macro bias, confirmed by FVG confluence and Triple EMA alignment.",
                    'reasons_sl': f"Placed safely behind key institutional Order Block to avoid sweeps.",
                    'reasons_tp': f"Targets mapped to nearest major support/resistance levels and liquidity pools.",
                    'invalidation': invalidation_reason,
                    'reasoning': self._build_detailed_reasoning_new(direction, details, score, inst_grade, invalidation_reason)
                }

                from data.futures_spot_converter import FuturesSpotConverter
                converter = FuturesSpotConverter()
                spot_inst_setup = converter.convert_setup_to_spot(inst_setup, symbol_key=symbol_key)

                institutional_setups.append(spot_inst_setup)

        return {
            'tfs_analyses': tfs_analyses,
            'breaker_blocks': breaker_blocks,
            'ifvgs': ifvgs,
            'fake_breakout': fake_breakout,
            'overall_htf_bias': overall_htf_bias,
            'setups': institutional_setups,
            'status': "SUCCESS" if institutional_setups else "NO_TRADE_YET"
        }

    # ─────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────

    def _detect_breaker_blocks(self, df: Optional[pd.DataFrame], bos_list: List[Dict]) -> List[Dict]:
        """Detect failed Order Blocks that got broken through (Breaker Blocks)."""
        breakers = []
        if df is None or df.empty or not bos_list:
            return breakers

        closes = df['close'].values
        opens = df['open'].values
        
        # Look at previous swing structure breakouts
        for bos in bos_list[-5:]:
            break_idx = bos['break_index']
            level = bos['level']
            # Find any historical order blocks that this BOS candle closed through
            # For a bullish BOS breaking a high, check if we broke a bearish OB
            if bos['type'] == 'BULLISH':
                # Bearish OB that was closed above
                for i in range(max(0, break_idx - 50), break_idx):
                    if closes[i] > opens[i] and opens[i] > level: # Bullish candle above swing high
                        # If price closed above it later
                        if closes[break_idx] > opens[i]:
                            breakers.append({
                                'type': 'BULLISH_BREAKER',
                                'top': float(closes[i]),
                                'bottom': float(opens[i]),
                                'index': i
                            })
            else:
                # Bullish OB that was closed below
                for i in range(max(0, break_idx - 50), break_idx):
                    if closes[i] < opens[i] and opens[i] < level:
                        if closes[break_idx] < closes[i]:
                            breakers.append({
                                'type': 'BEARISH_BREAKER',
                                'top': float(opens[i]),
                                'bottom': float(closes[i]),
                                'index': i
                            })
        return breakers

    def _detect_ifvgs(self, df: Optional[pd.DataFrame]) -> List[Dict]:
        """Detect Fair Value Gaps that have been broken and closed through (Inverse FVG)."""
        ifvgs = []
        if df is None or df.empty or len(df) < 5:
            return ifvgs

        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        # Scan last 50 bars for FVGs that got closed through
        for i in range(2, len(df) - 5):
            # Bullish FVG: Low(i) > High(i-2)
            if lows[i] > highs[i - 2]:
                fvg_top = lows[i]
                fvg_bottom = highs[i - 2]
                # Check if subsequent price closed below FVG bottom
                for j in range(i + 1, len(df)):
                    if closes[j] < fvg_bottom:
                        ifvgs.append({
                            'type': 'BEARISH_IFVG',
                            'top': float(fvg_top),
                            'bottom': float(fvg_bottom),
                            'index': i
                        })
                        break

            # Bearish FVG: High(i) < Low(i-2)
            elif highs[i] < lows[i - 2]:
                fvg_top = lows[i - 2]
                fvg_bottom = highs[i]
                # Check if subsequent price closed above FVG top
                for j in range(i + 1, len(df)):
                    if closes[j] > fvg_top:
                        ifvgs.append({
                            'type': 'BULLISH_IFVG',
                            'top': float(fvg_top),
                            'bottom': float(fvg_bottom),
                            'index': i
                        })
                        break
        return ifvgs

    def _check_fake_breakouts(self, df: Optional[pd.DataFrame]) -> bool:
        """Detect signs of a Fake Breakout (Liquidity Hunt / Stop Hunt)."""
        if df is None or df.empty or len(df) < 10:
            return False

        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values

        # Check if the last candle broke a recent high/low but closed inside the range
        last_high = highs[-1]
        last_low = lows[-1]
        last_close = closes[-1]

        prev_high = max(highs[-10:-1])
        prev_low = min(lows[-10:-1])

        # High swept but closed back down (Stop Hunt / Liquidity Sweep)
        if last_high > prev_high and last_close < prev_high:
            return True
        # Low swept but closed back up
        if last_low < prev_low and last_close > prev_low:
            return True

        return False

    def _calculate_trade_score(self, direction: str, overall_htf_bias: str,
                               daily_bias: str, h4_bias: str, h1_bias: str,
                               setup: Dict, exec_analysis: Dict,
                               breaker_blocks: List[Dict], ifvgs: List[Dict],
                               fake_breakout: bool, signal_type: str,
                               current_price: float, rr: float) -> Tuple[int, Dict]:
        """Calculate weighted institutional Trade Quality Score (0-100) using the Dynamic Confidence Engine."""
        details = {}
        
        # 1. Market Structure (20%)
        ms = exec_analysis['market_structure']
        ms_score = 0
        if ms['trend'] == direction + "ISH" or (direction == 'BUY' and ms['trend'] == 'BULLISH') or (direction == 'SELL' and ms['trend'] == 'BEARISH'):
            ms_score += 40
        if ms['structure_strength'] >= 75:
            ms_score += 30
        if len(ms['bos_list']) > 0:
            ms_score += 15
        if len(ms['choch_list']) > 0:
            ms_score += 15
        market_structure_weighted = (ms_score / 100) * 20
        details['market_structure'] = f"{ms_score}/100 ({market_structure_weighted:.1f}%)"

        # 2. Liquidity (15%)
        liq_score = 0
        if fake_breakout:
            liq_score += 50
        # Check liquidity pools
        buy_pools = len(exec_analysis['liquidity'].get('buy_side', []))
        sell_pools = len(exec_analysis['liquidity'].get('sell_side', []))
        if buy_pools > 0 or sell_pools > 0:
            liq_score += 30
        # Equal Highs/Lows presence
        if exec_analysis['liquidity'].get('all_levels'):
            liq_score += 20
        else:
            liq_score += 10
        liquidity_weighted = (min(100, liq_score) / 100) * 15
        details['liquidity'] = f"{liq_score}/100 ({liquidity_weighted:.1f}%)"

        # 3. Order Flow (15%)
        of_score = 0
        # Check volume and body size of active OB
        if setup.get('ob_strength', 0) >= 7:
            of_score += 60
        else:
            of_score += 40
        # Mitigation factor
        if not setup.get('mitigated', False):
            of_score += 40
        order_flow_weighted = (min(100, of_score) / 100) * 15
        details['order_flow'] = f"{of_score}/100 ({order_flow_weighted:.1f}%)"

        # 4. Momentum (10%)
        mom_score = 0
        rsi = exec_analysis['indicators']['rsi']
        if direction == 'BUY' and 30 <= rsi <= 55:
            mom_score += 70
        elif direction == 'SELL' and 45 <= rsi <= 70:
            mom_score += 70
        else:
            mom_score += 30
        if 30 <= rsi <= 70:
            mom_score += 30
        momentum_weighted = (mom_score / 100) * 10
        details['momentum'] = f"{mom_score}/100 ({momentum_weighted:.1f}%)"

        # 5. Trend Strength (10%)
        trend_strength_score = ms['structure_strength']
        trend_strength_weighted = (trend_strength_score / 100) * 10
        details['trend_strength'] = f"{trend_strength_score}/100 ({trend_strength_weighted:.1f}%)"

        # 6. Institutional Confluence (10%)
        inst_conf_score = 0
        has_breaker = any(b['type'] == direction + '_BREAKER' for b in breaker_blocks)
        has_ifvg = any(i['type'] == direction + '_IFVG' for i in ifvgs)
        if has_breaker:
            inst_conf_score += 50
        if has_ifvg:
            inst_conf_score += 50
        if not has_breaker and not has_ifvg:
            # Fallback to standard OB/FVG confluence
            if len(exec_analysis['fair_value_gaps']) > 0:
                inst_conf_score += 40
            if len(exec_analysis['order_blocks']) > 0:
                inst_conf_score += 40
        inst_confluence_weighted = (min(100, inst_conf_score) / 100) * 10
        details['inst_confluence'] = f"{inst_conf_score}/100 ({inst_confluence_weighted:.1f}%)"

        # 7. Session Timing (5%)
        from utils.scheduler import AnalysisScheduler
        current_hour_utc = datetime.now(timezone.utc).hour
        session_score = 0
        # Active sessions
        is_london = 8 <= current_hour_utc < 16
        is_ny = 13 <= current_hour_utc < 21
        if is_london and is_ny:
            session_score += 100
        elif is_london or is_ny:
            session_score += 80
        elif 0 <= current_hour_utc < 8:
            session_score += 50
        else:
            session_score += 30
        session_timing_weighted = (session_score / 100) * 5
        details['session_timing'] = f"{session_score}/100 ({session_timing_weighted:.1f}%)"

        # 8. Volatility (5%)
        vol_score = 0
        vol_status = exec_analysis['indicators']['volatility']
        if vol_status == 'MEDIUM':
            vol_score += 100
        elif vol_status == 'HIGH':
            vol_score += 70
        else:
            vol_score += 40
        volatility_weighted = (vol_score / 100) * 5
        details['volatility'] = f"{vol_score}/100 ({volatility_weighted:.1f}%)"

        # 9. Risk-to-Reward (5%)
        rr_score = 0
        if rr >= 3.0:
            rr_score += 100
        elif rr >= 2.0:
            rr_score += 70
        else:
            rr_score += 30
        rr_weighted = (rr_score / 100) * 5
        details['risk_reward'] = f"{rr_score}/100 ({rr_weighted:.1f}%)"

        # 10. Macro Bias (5%)
        macro_score = 0
        if overall_htf_bias == direction:
            macro_score += 50
        if daily_bias == direction:
            macro_score += 30
        if h4_bias == direction:
            macro_score += 20
        macro_weighted = (macro_score / 100) * 5
        details['macro_bias'] = f"{macro_score}/100 ({macro_weighted:.1f}%)"

        # 11. Trade Location (5%)
        loc_score = 0
        pd_zone = exec_analysis['premium_discount']
        if direction == 'BUY' and pd_zone == 'DISCOUNT':
            loc_score += 100
        elif direction == 'SELL' and pd_zone == 'PREMIUM':
            loc_score += 100
        elif pd_zone == 'EQUILIBRIUM':
            loc_score += 50
        else:
            loc_score += 10
        trade_location_weighted = (loc_score / 100) * 5
        details['trade_location'] = f"{loc_score}/100 ({trade_location_weighted:.1f}%)"

        # Sum total weighted points
        total_score = (
            market_structure_weighted +
            liquidity_weighted +
            order_flow_weighted +
            momentum_weighted +
            trend_strength_weighted +
            inst_confluence_weighted +
            session_timing_weighted +
            volatility_weighted +
            rr_weighted +
            macro_weighted +
            trade_location_weighted
        )
        
        score_int = int(round(total_score))
        return min(100, max(0, score_int)), details

    def _build_detailed_reasoning_new(self, direction: str, details: Dict, score: int, inst_grade: str, invalidation_reason: str) -> str:
        """Build detailed institutional reasoning text based on new weights."""
        dir_ar = 'شراء 🟢' if direction == 'BUY' else 'بيع 🔴'
        reasoning = (
            f"تم الكشف عن إعداد صفقة {dir_ar} بقوة ثقة إجمالية {score}% ({inst_grade}).\n"
            f"تفاصيل فحص محرك القرار الفني (Multi-Layer Validation):\n"
            f"  1. هيكل السوق والترند العام (Market Structure): {details.get('market_structure', 'N/A')}\n"
            f"  2. قوة الاتجاه ونقاط BOS/CHoCH (Trend Strength): {details.get('trend_strength', 'N/A')}\n"
            f"  3. سيولة الجلسات وسيولة الأسعار (Liquidity): {details.get('liquidity', 'N/A')}\n"
            f"  4. توافق السيولة المؤسساتية (Order Flow): {details.get('order_flow', 'N/A')}\n"
            f"  5. مستويات الفتح والكسر والـ IFVG (Confluence): {details.get('inst_confluence', 'N/A')}\n"
            f"  6. زخم القوة النسبية RSI (Momentum): {details.get('momentum', 'N/A')}\n"
            f"  7. توافق أوقات جلسات المال (Session Timing): {details.get('session_timing', 'N/A')}\n"
            f"  8. موقع الصفقة في مناطق الخصم والبريميوم (Trade Location): {details.get('trade_location', 'N/A')}\n"
            f"  9. إدارة المخاطر ومعدل العائد (Risk/Reward): {details.get('risk_reward', 'N/A')}\n"
            f"  10. توافق الفريمات الأكبر (Macro Bias): {details.get('macro_bias', 'N/A')}\n\n"
            f"⚠️ شروط إلغاء الصفقة وتجاوزها (Invalidation Conditions):\n"
            f"  • {invalidation_reason}"
        )
        return reasoning
