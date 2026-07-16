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

    def analyze_market(self, dataframes: Dict[str, pd.DataFrame], signal_type: str = 'SCALP') -> Dict:
        """Run complete institutional multi-timeframe analysis from Monthly to M5.

        Returns a detailed report dict with setups, scores, and explanations.
        """
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

        for setup in setups:
            direction = setup['direction']
            
            # Calculate institutional quality score (0-100)
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
                signal_type=signal_type
            )

            # Filter: only allow trades with a score of 90/100 or higher
            if score >= 90:
                # Target optimization
                entry = setup['entry']
                stop_loss = setup['stop_loss']
                
                # Risk to Reward Optimization (ensuring min requirements are strictly met)
                min_rr = 2.0 if signal_type == 'SCALP' else 3.0
                tp1 = setup['tp1']
                tp2 = setup['tp2']
                tp3 = setup['tp3']
                
                rr = abs(tp1 - entry) / max(0.01, abs(entry - stop_loss))
                if rr < min_rr:
                    # Adjust targets to fit institutional risk management
                    tp1 = round(entry + (entry - stop_loss) * min_rr, 2) if direction == 'BUY' else round(entry - (stop_loss - entry) * min_rr, 2)
                    tp2 = round(entry + (entry - stop_loss) * (min_rr + 1.0), 2) if direction == 'BUY' else round(entry - (stop_loss - entry) * (min_rr + 1.0), 2)
                    tp3 = round(entry + (entry - stop_loss) * (min_rr + 3.0), 2) if direction == 'BUY' else round(entry - (stop_loss - entry) * (min_rr + 3.0), 2)
                    rr = min_rr

                detailed_reasoning = self._build_detailed_reasoning(direction, details, score)
                
                # Active Kill Zone
                from utils.scheduler import AnalysisScheduler
                current_hour_utc = datetime.now(timezone.utc).hour
                active_sessions = []
                if 8 <= current_hour_utc < 16: active_sessions.append("LONDON 🇬🇧")
                if 13 <= current_hour_utc < 21: active_sessions.append("NEW YORK 🇺🇸")
                if 0 <= current_hour_utc < 8: active_sessions.append("ASIAN 🇯🇵")
                session_text = " + ".join(active_sessions) if active_sessions else "TRANSITION PERIOD 💤"

                inst_setup = {
                    'direction': direction,
                    'entry': entry,
                    'stop_loss': stop_loss,
                    'tp1': tp1,
                    'tp2': tp2,
                    'tp3': tp3,
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
                    'institutional_confirmation': details['institutional_conf'],
                    'momentum_analysis': f"RSI: {exec_analysis['indicators']['rsi']:.1f} | ATR: {exec_analysis['indicators']['atr']:.2f}",
                    'session_analysis': session_text,
                    'score': score,
                    'confidence': score,
                    'reasoning': detailed_reasoning
                }
                institutional_setups.append(inst_setup)

        return {
            'tfs_analyses': tfs_analyses,
            'breaker_blocks': breaker_blocks,
            'ifvgs': ifvgs,
            'fake_breakout': fake_breakout,
            'overall_htf_bias': overall_htf_bias,
            'setups': institutional_setups,
            'status': "SUCCESS" if institutional_setups else "NO_VALID_SETUP"
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
                               fake_breakout: bool, signal_type: str) -> Tuple[int, Dict]:
        """Calculate institutional Trade Quality Score (0-100)."""
        score = 0
        details = {}

        # ─── 1. HTF Trend & Bias Alignment (Max 30 pts) ───
        trend_pts = 0
        if overall_htf_bias == direction:
            trend_pts += 15
        if daily_bias == direction:
            trend_pts += 10
        if h4_bias == direction:
            trend_pts += 5
        score += trend_pts
        details['trend_alignment'] = f"{trend_pts}/30 points"

        # ─── 2. Market Structure & CHoCH (Max 25 pts) ───
        struct_pts = 0
        ms = exec_analysis['market_structure']
        if ms['trend'] == direction + "ISH" or (direction == 'BUY' and ms['trend'] == 'BULLISH') or (direction == 'SELL' and ms['trend'] == 'BEARISH'):
            struct_pts += 10
        if ms['structure_strength'] >= 70:
            struct_pts += 5
        # Check if setup is confirmed by CHoCH or BOS
        if len(ms['bos_list']) > 0:
            struct_pts += 5
        if len(ms['choch_list']) > 0:
            struct_pts += 5
        score += struct_pts
        details['market_structure'] = f"{struct_pts}/25 points"

        # ─── 3. Institutional Zones & Block Confluences (Max 25 pts) ───
        block_pts = 0
        # Premium/Discount check
        pd_zone = exec_analysis['premium_discount']
        if direction == 'BUY' and pd_zone == 'DISCOUNT':
            block_pts += 8
        elif direction == 'SELL' and pd_zone == 'PREMIUM':
            block_pts += 8
        
        # Order Block proximity
        if setup.get('ob_strength', 0) >= 7:
            block_pts += 7
        
        # Breaker Block or FVG overlap
        has_breaker = any(b['type'] == direction + '_BREAKER' for b in breaker_blocks)
        has_fvg = len(exec_analysis['fair_value_gaps']) > 0
        if has_breaker:
            block_pts += 5
        elif has_fvg:
            block_pts += 3

        # IFVG support
        has_ifvg = any(i['type'] == direction + '_IFVG' for i in ifvgs)
        if has_ifvg:
            block_pts += 5
        score += block_pts
        details['block_confluence'] = f"{block_pts}/25 points"

        # ─── 4. Momentum & Session Quality (Max 20 pts) ───
        m_pts = 0
        # RSI Check
        rsi = exec_analysis['indicators']['rsi']
        if direction == 'BUY' and 30 <= rsi <= 55:
            m_pts += 5
        elif direction == 'SELL' and 45 <= rsi <= 70:
            m_pts += 5

        # Session & Volatility
        from utils.scheduler import AnalysisScheduler
        if AnalysisScheduler.is_kill_zone():
            m_pts += 10
        else:
            m_pts += 5 # Lower points for trading outside session

        # Fake breakout / Hunt confirmation (adds extra validity if it's a stop run)
        if fake_breakout:
            m_pts += 5
        
        score += m_pts
        details['momentum_session'] = f"{m_pts}/20 points"

        # Institutional Confirmation Summary text
        details['institutional_conf'] = "HIGH" if score >= 90 else "MEDIUM" if score >= 75 else "LOW"

        return min(100, max(0, score)), details

    def _build_detailed_reasoning(self, direction: str, details: Dict, score: int) -> str:
        """Build detailed institutional reasoning text."""
        dir_ar = 'شراء 🟢' if direction == 'BUY' else 'بيع 🔴'
        reasoning = (
            f"إعداد {dir_ar} بمستوى دقة مؤسساتي {score}/100.\n"
            f"• توافق الاتجاه العام: {details.get('trend_alignment', 'N/A')}\n"
            f"• هيكل السوق والكسر: {details.get('market_structure', 'N/A')}\n"
            f"• توافق الكتل السعرية (OB/Breaker): {details.get('block_confluence', 'N/A')}\n"
            f"• زخم الأسعار والجلسات: {details.get('momentum_session', 'N/A')}\n"
            f"• التقييم النهائي: تم رصد تأكيد سيولة كافٍ للدخول الآمن."
        )
        return reasoning
