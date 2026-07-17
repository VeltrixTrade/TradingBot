"""
Mustafa Bot - Automated Quantitative Strategy Unit Test & Defect Detection Suite
يقوم باختبار وتقييم كل استراتيجية تداول على حزم بيانات تاريخية وتحديد أي استراتيجية تالفة (Defective) لا تنتج إشارات.
"""

import unittest
import pandas as pd
import numpy as np
import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding='utf-8')

from analysis.strategies.smc_ict_strategy import SMC_ICT_ScalpStrategy
from analysis.strategies.price_action_strategy import PriceAction_ScalpStrategy
from analysis.strategies.liquidity_sweep_strategy import LiquiditySweep_ScalpStrategy
from analysis.strategies.breakout_strategy import Breakout_ScalpStrategy
from analysis.strategies.momentum_pullback_strategy import MomentumPullback_ScalpStrategy
from analysis.strategies.triple_ema_strategy import TripleEMA_ScalpStrategy


class TestTradingStrategies(unittest.TestCase):
    """Unit testing suite for quantitative scalping strategies."""

    @classmethod
    def setUpClass(cls):
        """Generate structured benchmark datasets representing trend, breakout, sweep, and pullbacks."""
        dates = pd.date_range('2026-07-01', periods=200, freq='15min')

        # 1. Bullish Rejection + Pinbar dataset
        np.random.seed(101)
        p1 = 2400.0 + np.cumsum(np.random.randn(200) * 0.5 + 0.3)
        df_bull = pd.DataFrame({
            'open': p1,
            'high': p1 + 5.0,
            'low': p1 - 15.0,  # Long lower wick (bullish pinbar)
            'close': p1 + 1.0,
            'tick_volume': np.random.randint(500, 2000, 200)
        }, index=dates)
        cls.tfs_bullish = {'15m': df_bull, '1h': df_bull, '4h': df_bull, '1d': df_bull}

        # 2. Bearish Rejection + Wick dataset
        np.random.seed(202)
        p2 = 2450.0 - np.cumsum(np.random.randn(200) * 0.5 + 0.4)
        df_bear = pd.DataFrame({
            'open': p2,
            'high': p2 + 15.0,  # Long upper wick (bearish pinbar)
            'low': p2 - 5.0,
            'close': p2 - 1.0,
            'tick_volume': np.random.randint(500, 2000, 200)
        }, index=dates)
        cls.tfs_bearish = {'15m': df_bear, '1h': df_bear, '4h': df_bear, '1d': df_bear}

        # 3. Volatility Breakout dataset (recent close breaks 15-candle high)
        p3 = np.full(200, 2400.0)
        p3[-1] = 2435.0  # Massive bullish breakout on last candle
        df_bo = pd.DataFrame({
            'open': p3 - 1.0,
            'high': p3 + 2.0,
            'low': p3 - 2.0,
            'close': p3,
            'tick_volume': 2000
        }, index=dates)
        cls.tfs_breakout = {'15m': df_bo, '1h': df_bo, '4h': df_bo, '1d': df_bo}

        # 4. RSI & Momentum Pullback dataset (RSI crosses 52)
        p4 = np.linspace(2400, 2410, 200)
        p4[-2] = 2405.0
        p4[-1] = 2425.0  # Big RSI jump
        df_rsi = pd.DataFrame({
            'open': p4 - 1.0,
            'high': p4 + 1.0,
            'low': p4 - 1.0,
            'close': p4,
            'tick_volume': 1000
        }, index=dates)
        cls.tfs_rsi = {'15m': df_rsi, '1h': df_rsi, '4h': df_rsi, '1d': df_rsi}

        # 5. Triple EMA Crossover dataset
        p5 = np.linspace(2300, 2400, 200)
        p5[-2] = 2390.0
        p5[-1] = 2420.0  # EMA5 crosses EMA20
        df_ema = pd.DataFrame({
            'open': p5 - 1.0,
            'high': p5 + 2.0,
            'low': p5 - 2.0,
            'close': p5,
            'tick_volume': 1000
        }, index=dates)
        cls.tfs_ema = {'15m': df_ema, '1h': df_ema, '4h': df_ema, '1d': df_ema}

        cls.strategies = [
            SMC_ICT_ScalpStrategy(),
            PriceAction_ScalpStrategy(),
            LiquiditySweep_ScalpStrategy(),
            Breakout_ScalpStrategy(),
            MomentumPullback_ScalpStrategy(),
            TripleEMA_ScalpStrategy()
        ]

    def test_all_strategies_evaluation(self):
        """Verify that every strategy produces valid setup evaluations without crashing or returning defects."""
        defective_strategies = []

        all_datasets = [
            self.tfs_bullish,
            self.tfs_bearish,
            self.tfs_breakout,
            self.tfs_rsi,
            self.tfs_ema
        ]

        for strat in self.strategies:
            strat_name = strat.name
            print(f"\nTesting Strategy: {strat_name}...")

            has_valid_setup = False
            for ds in all_datasets:
                res = strat.evaluate(ds, 'XAU/USD', '15m')
                if res is not None and res.get('direction') in ['BUY', 'SELL']:
                    has_valid_setup = True
                    break

            if not has_valid_setup:
                defective_strategies.append(strat_name)
                print(f"  [DEFECTIVE] Strategy {strat_name} produced NO setups during historical benchmark tests!")
            else:
                print(f"  [OK] Strategy {strat_name} generated valid setups successfully.")

        if defective_strategies:
            self.fail(f"DEFECTIVE STRATEGIES DETECTED: {defective_strategies}. These strategies failed to produce signals on benchmark data!")

if __name__ == '__main__':
    unittest.main()
