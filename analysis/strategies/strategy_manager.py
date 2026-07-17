"""
Mustafa Bot - Parallel Scalping Strategy Manager
إدارة وتشغيل كافة استراتيجيات التداول بالتوازي المستقل عبر asyncio.gather()
"""

import asyncio
import logging
from typing import Dict, List, Optional
import pandas as pd

from analysis.strategies.smc_ict_strategy import SMC_ICT_ScalpStrategy
from analysis.strategies.price_action_strategy import PriceAction_ScalpStrategy
from analysis.strategies.liquidity_sweep_strategy import LiquiditySweep_ScalpStrategy
from analysis.strategies.breakout_strategy import Breakout_ScalpStrategy
from analysis.strategies.momentum_pullback_strategy import MomentumPullback_ScalpStrategy
from analysis.strategies.triple_ema_strategy import TripleEMA_ScalpStrategy
from config import Config

logger = logging.getLogger('mustafa_bot.analysis.strategies.strategy_manager')


class ParallelStrategyManager:
    """Orchestrator for running multiple independent scalping strategies concurrently."""

    def __init__(self):
        self.strategies = [
            SMC_ICT_ScalpStrategy(),
            PriceAction_ScalpStrategy(),
            LiquiditySweep_ScalpStrategy(),
            Breakout_ScalpStrategy(),
            MomentumPullback_ScalpStrategy(),
            TripleEMA_ScalpStrategy()
        ]

    async def _evaluate_single(
        self,
        strategy,
        dataframes: Dict[str, pd.DataFrame],
        symbol: str,
        timeframe: str,
        min_score: int,
        min_rr: float
    ) -> Optional[Dict]:
        """Wrapper to run a single strategy evaluation safely in an executor."""
        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(
                None,
                strategy.evaluate,
                dataframes,
                symbol,
                timeframe,
                min_score,
                min_rr
            )
            return res
        except Exception as e:
            logger.error(f"Strategy '{strategy.name}' evaluation error: {e}", exc_info=True)
            return None

    async def evaluate_all_parallel(
        self,
        dataframes: Dict[str, pd.DataFrame],
        symbol: str = 'XAU/USD',
        timeframe: str = '15m',
        selectivity_profile: str = 'BALANCED'
    ) -> List[Dict]:
        """Evaluate all enabled scalping strategies simultaneously in parallel after passing Market Data Validation Gate."""
        from data.price_validator import MarketPriceValidator
        validator = MarketPriceValidator()

        # Pre-Analysis Market Data Quality & Price Validation Gate
        exec_df = dataframes.get(timeframe)
        if exec_df is not None:
            val_res = validator.validate_market_data(exec_df, symbol_key=symbol, timeframe=timeframe)
            if not val_res.is_valid:
                logger.warning(f"🛑 Scalping Pipeline Gate rejected setup generation for {symbol} ({timeframe}): {val_res.reason}")
                return []

        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        db_score = db.get_setting('min_score', '75')
        db_rr = db.get_setting('min_rr', '3.0')
        
        min_score = int(db_score) if db_score is not None else 75
        min_rr = float(db_rr) if db_rr is not None else 3.0

        tasks = [
            self._evaluate_single(strat, dataframes, symbol, timeframe, min_score, min_rr)
            for strat in self.strategies
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        from data.futures_spot_converter import FuturesSpotConverter
        converter = FuturesSpotConverter()

        valid_setups = []
        for r in results:
            if isinstance(r, dict) and r is not None:
                # Convert Futures levels to live Spot market prices
                spot_r = converter.convert_setup_to_spot(r, symbol_key=symbol)
                spot_r['validation_info'] = f"TradingView Validated ✅ (Diff: {val_res.discrepancy_pips:.2f} pips | Spread: {val_res.spread_pips:.1f} pips)"
                valid_setups.append(spot_r)

        return valid_setups
