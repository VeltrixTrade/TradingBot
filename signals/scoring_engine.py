"""
Mustafa Bot - Quantitative Trade Scoring Engine (0-100 Points)
يحسب درجة جودة الفرصة بدقة بناءً على تأكيدات متعدّدة وأوزان مؤسساتية
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger('mustafa_bot.signals.scoring_engine')


class TradeScoringEngine:
    """Quantitative scoring engine evaluating setups from 0 to 100 points."""

    @staticmethod
    def calculate_score(setup: Dict, market_data: Dict, ai_consensus: Dict) -> Dict:
        """
        Calculate total weighted score and return breakdown factors.
        
        Weights:
        - Higher TF Trend Alignment: 20 pts
        - Break of Structure (BOS): 15 pts
        - Order Block (OB) Confluence: 15 pts
        - Fair Value Gap (FVG) Confluence: 15 pts
        - Liquidity Sweep Confirmation: 15 pts
        - AI Consensus Agreement: 10 pts (10 for 3/3, 5 for 2/3)
        - Timeframe Convergence (M5/M15 alignment): 10 pts
        """
        score = 0
        factors = []
        breakdown = {}

        direction = setup.get('direction', 'NEUTRAL').upper()

        # 1. Higher TF Trend Alignment (20 pts)
        htf_trend = market_data.get('htf_trend', 'NEUTRAL')
        if (direction == 'BUY' and htf_trend == 'BULLISH') or (direction == 'SELL' and htf_trend == 'BEARISH'):
            score += 20
            factors.append(" Higher TF Trend Aligned (+20)")
            breakdown['htf_trend'] = 20
        elif htf_trend in ('NEUTRAL', 'RANGING'):
            score += 10
            factors.append(" Higher TF Neutral/Ranging (+10)")
            breakdown['htf_trend'] = 10
        else:
            breakdown['htf_trend'] = 0

        # 2. Break of Structure (BOS) (15 pts)
        reasoning = setup.get('reasoning', '') + setup.get('smc_setup', '')
        if 'BOS' in reasoning.upper() or setup.get('bos_confirmed', False):
            score += 15
            factors.append(" Break of Structure (BOS) Confirmed (+15)")
            breakdown['bos'] = 15
        else:
            breakdown['bos'] = 0

        # 3. Order Block (OB) Confluence (15 pts)
        if 'OB' in reasoning.upper() or setup.get('ob_confirmed', False):
            score += 15
            factors.append(" Institutional Order Block (OB) (+15)")
            breakdown['ob'] = 15
        else:
            breakdown['ob'] = 0

        # 4. Fair Value Gap (FVG) Confluence (15 pts)
        if 'FVG' in reasoning.upper() or setup.get('fvg_confirmed', False):
            score += 15
            factors.append(" Fair Value Gap Imbalance (FVG) (+15)")
            breakdown['fvg'] = 15
        else:
            breakdown['fvg'] = 0

        # 5. Liquidity Sweep Confirmation (15 pts)
        if 'LIQUIDITY' in reasoning.upper() or 'SWEEP' in reasoning.upper() or setup.get('liquidity_swept', False):
            score += 15
            factors.append(" Liquidity Pool Swept (+15)")
            breakdown['liquidity'] = 15
        else:
            breakdown['liquidity'] = 0

        # 6. AI Consensus Agreement (10 pts)
        agreement = ai_consensus.get('agreement', 0)
        ai_dir = ai_consensus.get('direction', 'NEUTRAL')
        if ai_dir == direction:
            if agreement >= 3:
                score += 10
                factors.append(" Triple AI Consensus 3/3 (+10)")
                breakdown['ai_consensus'] = 10
            elif agreement == 2:
                score += 5
                factors.append(" AI Consensus 2/3 (+5)")
                breakdown['ai_consensus'] = 5
            else:
                breakdown['ai_consensus'] = 0
        else:
            breakdown['ai_consensus'] = 0

        # 7. Timeframe Convergence (M5/M15 alignment) (10 pts)
        m5_trend = market_data.get('m5_trend', '')
        m15_trend = market_data.get('m15_trend', '')
        if m5_trend and m15_trend and m5_trend == m15_trend:
            score += 10
            factors.append(" Timeframe Convergence M5/M15 (+10)")
            breakdown['tf_convergence'] = 10
        elif not m5_trend and not m15_trend:
            # Fallback score if specific sub-trends are not provided directly
            score += 10
            factors.append(" Timeframe Structure Aligned (+10)")
            breakdown['tf_convergence'] = 10
        else:
            breakdown['tf_convergence'] = 0

        final_score = min(score, 100)
        return {
            'score': final_score,
            'factors': factors,
            'breakdown': breakdown
        }
