"""
Mustafa Bot - Signal Generator
مولّد الإشارات من تحليل SMC + AI
"""

import uuid
import logging
from typing import List, Dict
from datetime import datetime

from signals.models import Signal, SignalType, Direction, SignalStatus
from config import Config

logger = logging.getLogger('mustafa_bot.signals.generator')


class SignalGenerator:
    """Generates trading signals by combining SMC/ICT analysis with AI consensus."""

    def __init__(self):
        self.daily_scalp_count = 0
        self.daily_swing_count = 0
        self.last_reset_date = datetime.utcnow().date()

    def generate_signals(self, smc_analysis: Dict, ai_consensus: Dict,
                          signal_type: str = 'SCALP', timeframe: str = 'M15',
                          current_price: float = 0.0, is_manual: bool = False) -> List[Signal]:
        """Generate signals from combined SMC + AI analysis."""
        self._reset_daily_counts()

        # Check daily limits (only for automated signals)
        if not is_manual:
            if signal_type == 'SCALP' and self.daily_scalp_count >= Config.MAX_DAILY_SCALP_SIGNALS:
                logger.info('Daily scalp signal limit reached')
                return []
            if signal_type == 'SWING' and self.daily_swing_count >= Config.MAX_DAILY_SWING_SIGNALS:
                logger.info('Daily swing signal limit reached')
                return []

        # Get setups from SMC analysis
        setups = smc_analysis.get('setups', [])
        if not setups:
            logger.info('No SMC setups found')
            return []

        # Check AI consensus (only for automated signals)
        ai_direction = ai_consensus.get('direction', 'NEUTRAL')
        if not is_manual:
            if not ai_consensus.get('consensus_reached', False) or ai_direction == 'NEUTRAL':
                logger.info('No AI consensus reached, skipping automated signal generation')
                return []

        signals = []
        for setup in setups:
            # Setup direction must match AI consensus (only for automated signals)
            if not is_manual:
                if setup['direction'] != ai_direction:
                    continue

            signal = self._create_signal_from_setup(
                setup, ai_consensus, signal_type, timeframe, current_price
            )

            # Relax confidence requirement for manual queries to ensure setup delivery
            min_conf = Config.MIN_CONFIDENCE - 15 if is_manual else Config.MIN_CONFIDENCE
            if signal and signal.confidence >= min_conf:
                signals.append(signal)

                # Update daily counts
                if signal_type == 'SCALP':
                    self.daily_scalp_count += 1
                else:
                    self.daily_swing_count += 1

        logger.info(f'Generated {len(signals)} {signal_type} signals')
        return signals

    def _create_signal_from_setup(self, setup: Dict, ai_consensus: Dict,
                                    signal_type: str, timeframe: str,
                                    current_price: float) -> Signal:
        """Create a Signal from an SMC setup + AI consensus."""
        try:
            direction = Direction.BUY if setup['direction'] == 'BUY' else Direction.SELL
            sig_type = SignalType.SCALP if signal_type == 'SCALP' else SignalType.SWING

            # Use SMC levels as primary, AI levels to adjust
            entry = setup['entry']
            stop_loss = setup['stop_loss']
            tp1 = setup['tp1']
            tp2 = setup['tp2']
            tp3 = setup['tp3']

            # If AI has valid levels, blend them (70% SMC, 30% AI)
            ai_entry = ai_consensus.get('entry', 0)
            ai_sl = ai_consensus.get('stop_loss', 0)
            ai_tp1 = ai_consensus.get('take_profit_1', 0)
            ai_tp2 = ai_consensus.get('take_profit_2', 0)
            ai_tp3 = ai_consensus.get('take_profit_3', 0)

            if ai_entry > 0 and abs(ai_entry - entry) < abs(entry - stop_loss):
                entry = round(entry * 0.7 + ai_entry * 0.3, 2)
            if ai_sl > 0 and abs(ai_sl - stop_loss) < abs(entry - stop_loss) * 2:
                stop_loss = round(stop_loss * 0.7 + ai_sl * 0.3, 2)
            if ai_tp1 > 0:
                tp1 = round(tp1 * 0.7 + ai_tp1 * 0.3, 2)
            if ai_tp2 > 0:
                tp2 = round(tp2 * 0.7 + ai_tp2 * 0.3, 2)
            if ai_tp3 > 0:
                tp3 = round(tp3 * 0.7 + ai_tp3 * 0.3, 2)

            # Calculate R:R
            risk_reward = self._calculate_risk_reward(entry, stop_loss, tp1)

            # Calculate confidence
            smc_score = setup.get('score', 50)
            ai_confidence = ai_consensus.get('confidence', 50)
            ai_agreement = ai_consensus.get('agreement', 0)
            confidence = self._calculate_confidence(smc_score, ai_confidence, ai_agreement)

            # Build analysis text
            analysis_text = self._build_analysis_text(setup, ai_consensus)

            # Prediction and reversal zones
            prediction = ai_consensus.get('prediction', '')
            reversal_zones = ai_consensus.get('reversal_zones', [])

            # SMC setup name
            smc_setup = ' + '.join(setup.get('confluence_list', ['Order Block']))

            signal = Signal(
                id=str(uuid.uuid4())[:8],
                type=sig_type,
                direction=direction,
                entry=entry,
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_reward=round(risk_reward, 2),
                confidence=confidence,
                timeframe=timeframe,
                smc_setup=smc_setup,
                ai_consensus=ai_consensus.get('consensus_text', ''),
                ai_agreement=ai_agreement,
                analysis_text=analysis_text,
                prediction=prediction,
                reversal_zones=reversal_zones,
                status=SignalStatus.ACTIVE,
            )

            return signal

        except Exception as e:
            logger.error(f'Error creating signal: {e}')
            return None

    def _calculate_risk_reward(self, entry: float, sl: float, tp: float) -> float:
        """Calculate risk/reward ratio."""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk <= 0:
            return 0.0
        return reward / risk

    def _calculate_confidence(self, smc_score: int, ai_confidence: int,
                               ai_agreement: int) -> int:
        """Calculate overall confidence (0-100)."""
        # SMC score weight: 40%
        smc_part = smc_score * 0.4
        # AI confidence weight: 40%
        ai_part = ai_confidence * 0.4
        # AI agreement bonus: 20% (2/3 = 10%, 3/3 = 20%)
        agreement_bonus = 0
        if ai_agreement >= 3:
            agreement_bonus = 20
        elif ai_agreement >= 2:
            agreement_bonus = 10

        total = smc_part + ai_part + agreement_bonus
        return min(100, max(0, int(total)))

    def _build_analysis_text(self, setup: Dict, ai_consensus: Dict) -> str:
        """Build Arabic analysis text for the signal."""
        direction_ar = 'شراء' if setup['direction'] == 'BUY' else 'بيع'
        confluences = ' + '.join(setup.get('confluence_list', []))

        text = f"إشارة {direction_ar} بناءً على {setup.get('confluence_count', 0)} تقاطعات SMC/ICT:\n"
        text += f"• {confluences}\n"
        text += f"• {setup.get('description', '')}\n"

        # Triple EMA confirmation
        ema_confirmed = setup.get('ema_confirmed')
        ema_reason = setup.get('ema_reason', '')
        if ema_confirmed is not None:
            if ema_confirmed:
                text += f"\n📊 Triple EMA: {ema_reason}\n"
            else:
                text += f"\n⚠️ Triple EMA: {ema_reason}\n"

        if ai_consensus.get('reasoning'):
            # Take first 200 chars of reasoning for brevity
            reasoning = ai_consensus['reasoning'][:300]
            text += f"\n🤖 تحليل AI:\n{reasoning}"

        return text

    def _reset_daily_counts(self):
        """Reset daily signal counts if new day."""
        today = datetime.utcnow().date()
        if today != self.last_reset_date:
            self.daily_scalp_count = 0
            self.daily_swing_count = 0
            self.last_reset_date = today
            logger.info('Daily signal counts reset')
