"""
Mustafa Bot - Quantitative Signal Generator with Multi-Stage Validation Pipeline
مولّد الإشارات المتقدم بنظام الفحص المؤسساتي المتعدد المراحل وتقييم جودة الصفقات
"""

import uuid
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from signals.models import Signal, SignalType, Direction, SignalStatus
from signals.scoring_engine import TradeScoringEngine
from database.db_manager import DatabaseManager
from config import Config

logger = logging.getLogger('mustafa_bot.signals.generator')


class SignalGenerator:
    """Generates and validates quantitative trading signals with zero tolerance for random setups."""

    def __init__(self):
        self.daily_scalp_count = 0
        self.daily_swing_count = 0
        self.last_reset_date = datetime.now(timezone.utc).date()
        self.db = DatabaseManager()

    def generate_signals(self, smc_analysis: Dict, ai_consensus: Dict,
                          signal_type: str = 'SCALP', timeframe: str = 'M15',
                          current_price: float = 0.0, is_manual: bool = False,
                          symbol_key: str = 'XAU/USD') -> List[Signal]:
        """Generate signals by executing full multi-stage quantitative validation pipeline."""
        self._reset_daily_counts()

        # Check daily signal limits
        if not is_manual:
            if signal_type == 'SCALP' and self.daily_scalp_count >= Config.MAX_DAILY_SCALP_SIGNALS:
                logger.info(f"Daily scalp signal limit ({Config.MAX_DAILY_SCALP_SIGNALS}) reached")
                self.db.insert_rejected_signal(symbol_key, "NONE", 0, 0.0, "REJECTED_DAILY_LIMIT", "Reached max daily scalp limit")
                return []
            if signal_type == 'SWING' and self.daily_swing_count >= Config.MAX_DAILY_SWING_SIGNALS:
                logger.info(f"Daily swing signal limit ({Config.MAX_DAILY_SWING_SIGNALS}) reached")
                self.db.insert_rejected_signal(symbol_key, "NONE", 0, 0.0, "REJECTED_DAILY_LIMIT", "Reached max daily swing limit")
                return []

        setups = smc_analysis.get('setups', [])
        if not setups:
            logger.info(f"No technical SMC setups detected for {symbol_key}")
            self.db.insert_rejected_signal(symbol_key, "NONE", 0, 0.0, "REJECTED_NO_SMC_SETUP", "SMC/ICT engine found zero structure setups")
            return []

        ai_direction = ai_consensus.get('direction', 'NEUTRAL')

        signals = []
        for setup in setups:
            signal, reject_reason = self._validate_and_create_signal(
                setup, ai_consensus, smc_analysis, signal_type, timeframe, current_price, is_manual, symbol_key
            )

            if signal:
                signals.append(signal)
                if signal_type == 'SCALP':
                    self.daily_scalp_count += 1
                else:
                    self.daily_swing_count += 1
            else:
                logger.info(f"🚫 Setup for {symbol_key} rejected by pipeline: {reject_reason}")

        logger.info(f"🎯 Generated {len(signals)} validated high-quality {signal_type} signals for {symbol_key}")
        return signals

    def _validate_and_create_signal(self, setup: Dict, ai_consensus: Dict, market_data: Dict,
                                     signal_type: str, timeframe: str, current_price: float,
                                     is_manual: bool, symbol_key: str) -> Tuple[Optional[Signal], str]:
        """Multi-stage validation pipeline for trade setups."""
        direction_str = setup.get('direction', 'BUY').upper()
        entry = setup.get('entry', 0.0)
        stop_loss = setup.get('stop_loss', 0.0)
        tp1 = setup.get('tp1', 0.0)
        tp2 = setup.get('tp2', 0.0)
        tp3 = setup.get('tp3', 0.0)

        # ── STAGE 1: Level Geometry Math Validation ──
        if entry <= 0 or stop_loss <= 0 or tp1 <= 0:
            reason = "REJECTED_INVALID_LEVELS"
            self.db.insert_rejected_signal(symbol_key, direction_str, 0, 0.0, reason, "Price levels contain invalid zero or negative numbers")
            return None, reason

        if direction_str == 'BUY':
            if not (entry > stop_loss and tp1 > entry and tp2 >= tp1 and tp3 >= tp2):
                reason = "REJECTED_GEOMETRY_BUY_MISMATCH"
                self.db.insert_rejected_signal(symbol_key, direction_str, 0, 0.0, reason, f"BUY geometry invalid: Entry={entry}, SL={stop_loss}, TP1={tp1}")
                return None, reason
        elif direction_str == 'SELL':
            if not (entry < stop_loss and tp1 < entry and tp2 <= tp1 and tp3 <= tp2):
                reason = "REJECTED_GEOMETRY_SELL_MISMATCH"
                self.db.insert_rejected_signal(symbol_key, direction_str, 0, 0.0, reason, f"SELL geometry invalid: Entry={entry}, SL={stop_loss}, TP1={tp1}")
                return None, reason

        # ── STAGE 2: Risk / Reward Strict Threshold ──
        risk = abs(entry - stop_loss)
        reward = abs(tp3 - entry) if tp3 > 0 else abs(tp1 - entry)
        risk_reward = round(reward / risk, 2) if risk > 0 else 0.0

        # Read configured minimum R:R or default to 3.0
        db_rr = self.db.get_setting('min_rr')
        target_rr = float(db_rr) if db_rr is not None else 3.0
        if is_manual:
            target_rr = max(1.5, target_rr - 1.0)  # Relaxed slightly for manual query review

        if risk_reward < target_rr:
            reason = "REJECTED_INSUFFICIENT_RR"
            self.db.insert_rejected_signal(symbol_key, direction_str, 0, risk_reward, reason, f"Risk/Reward {risk_reward} below minimum threshold 1:{target_rr}")
            return None, reason

        # ── STAGE 3: Spread & Volatility Check ──
        from data.mt5_connection import MT5ConnectionManager
        sym_info = MT5ConnectionManager().get_symbol_info(symbol_key)
        spread_pips = sym_info['spread_pips'] if sym_info else 0.3
        max_allowed_spread = Config.MAX_ALLOWED_SPREAD_PIPS

        if spread_pips > max_allowed_spread:
            reason = "REJECTED_EXCESSIVE_SPREAD"
            self.db.insert_rejected_signal(symbol_key, direction_str, 0, risk_reward, reason, f"Current spread {spread_pips} pips exceeds limit {max_allowed_spread}")
            return None, reason

        # ── STAGE 4: Quantitative Score Engine Evaluation ──
        scoring_res = TradeScoringEngine.calculate_score(setup, market_data, ai_consensus)
        calculated_score = scoring_res['score']
        factors = scoring_res['factors']

        db_score = self.db.get_setting('min_score')
        min_required_score = int(db_score) if db_score is not None else 90
        if is_manual:
            min_required_score = max(75, min_required_score - 10)

        if calculated_score < min_required_score:
            reason = "REJECTED_LOW_CONFIDENCE_SCORE"
            details = f"Score {calculated_score}/100 below required {min_required_score}. Factors: {', '.join(factors)}"
            self.db.insert_rejected_signal(symbol_key, direction_str, calculated_score, risk_reward, reason, details)
            return None, reason

        # ── STAGE 5: Duplicate Active Signal Prevention ──
        if not is_manual:
            active_trades = self.db.get_active_trades()
            for trade in active_trades:
                if trade['symbol'] == symbol_key and trade['direction'] == direction_str:
                    reason = "REJECTED_DUPLICATE_ACTIVE_TRADE"
                    details = f"Active trade {trade['id']} already running on {symbol_key} in direction {direction_str}"
                    self.db.insert_rejected_signal(symbol_key, direction_str, calculated_score, risk_reward, reason, details)
                    return None, reason

        # ── SUCCESS: Construct Validated Signal Object ──
        direction = Direction.BUY if direction_str == 'BUY' else Direction.SELL
        sig_type = SignalType.SCALP if signal_type == 'SCALP' else SignalType.SWING
        smc_setup = ' + '.join(setup.get('confluence_list', ['Order Block', 'BOS']))

        factors_summary = "\n".join([f"• {f}" for f in factors])
        analysis_text = (
            f"🎯 *تأكيدات الصفقة المؤسساتية (Trade Quality Score: {calculated_score}/100)*:\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{factors_summary}\n\n"
            f"🤖 *الذكاء الاصطناعي*: {ai_consensus.get('consensus_text', 'متوافق')}"
        )

        signal = Signal(
            id=str(uuid.uuid4())[:8],
            type=sig_type,
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_reward=risk_reward,
            confidence=calculated_score,
            timeframe=timeframe,
            smc_setup=smc_setup,
            ai_consensus=ai_consensus.get('consensus_text', ''),
            ai_agreement=ai_consensus.get('agreement', 0),
            analysis_text=analysis_text,
            prediction=ai_consensus.get('prediction', ''),
            reversal_zones=ai_consensus.get('reversal_zones', []),
            status=SignalStatus.ACTIVE,
        )

        logger.info(f"✅ Setup for {symbol_key} ACCEPTED! Score: {calculated_score}/100 | RR: 1:{risk_reward}")
        return signal, "SUCCESS"

    def _reset_daily_counts(self):
        """Reset daily signal counts on date change."""
        today = datetime.now(timezone.utc).date()
        if today != self.last_reset_date:
            self.daily_scalp_count = 0
            self.daily_swing_count = 0
            self.last_reset_date = today
            logger.info("Daily signal counts reset for new day UTC")
