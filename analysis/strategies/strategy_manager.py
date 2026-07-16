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
        """Evaluate all enabled scalping strategies simultaneously in parallel."""
        prof_cfg = Config.SELECTIVITY_PROFILES.get(
            selectivity_profile,
            Config.SELECTIVITY_PROFILES[Config.DEFAULT_SELECTIVITY]
        )
        min_score = prof_cfg['min_score']
        min_rr = prof_cfg['min_rr']

        tasks = [
            self._evaluate_single(strat, dataframes, symbol, timeframe, min_score, min_rr)
            for strat in self.strategies
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_setups = []
        for r in results:
            if isinstance(r, dict) and r is not None:
                valid_setups.append(r)

        return valid_setups
