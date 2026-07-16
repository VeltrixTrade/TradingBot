"""
Mustafa Bot - Abstract Base Strategy Module
الفئة الأساسية لجميع استراتيجيات السكالبينغ المستقلة والمتوازية
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd


class BaseScalpingStrategy(ABC):
    """Abstract Base Class for all low-latency parallel scalping strategies."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def evaluate(
        self,
        dataframes: Dict[str, pd.DataFrame],
        symbol: str = 'XAU/USD',
        timeframe: str = '15m',
        min_score: int = 82,
        min_rr: float = 2.0
    ) -> Optional[Dict]:
        """Evaluate market data independently and return setup dictionary if valid score >= min_score."""
        pass
