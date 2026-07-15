"""
Mustafa Bot - Data Models
نماذج البيانات الأساسية للإشارات والتحليل
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class SignalType(Enum):
    SCALP = 'SCALP'
    SWING = 'SWING'


class Direction(Enum):
    BUY = 'BUY'
    SELL = 'SELL'


class SignalStatus(Enum):
    ACTIVE = 'ACTIVE'
    TP1_HIT = 'TP1_HIT'
    TP2_HIT = 'TP2_HIT'
    TP3_HIT = 'TP3_HIT'
    SL_HIT = 'SL_HIT'
    EXPIRED = 'EXPIRED'


@dataclass
class MarketStructure:
    trend: str = 'NEUTRAL'
    last_bos: Optional[float] = None
    last_choch: Optional[float] = None
    swing_high: Optional[float] = None
    swing_low: Optional[float] = None
    strength: int = 0


@dataclass
class OrderBlock:
    type: str = ''
    top: float = 0.0
    bottom: float = 0.0
    strength: int = 0
    mitigated: bool = False
    timeframe: str = ''


@dataclass
class FairValueGap:
    type: str = ''
    top: float = 0.0
    bottom: float = 0.0
    fill_percentage: float = 0.0
    timeframe: str = ''


@dataclass
class LiquidityZone:
    type: str = ''
    level: float = 0.0
    strength: int = 0
    swept: bool = False


@dataclass
class SMCAnalysis:
    market_structure: MarketStructure = field(default_factory=MarketStructure)
    order_blocks: List[OrderBlock] = field(default_factory=list)
    fair_value_gaps: List[FairValueGap] = field(default_factory=list)
    liquidity_zones: List[LiquidityZone] = field(default_factory=list)
    premium_discount: str = ''
    overall_bias: str = ''
    score: int = 0
    key_levels: List[float] = field(default_factory=list)


@dataclass
class AIAnalysis:
    provider: str = ''
    direction: str = ''
    confidence: int = 0
    entry: float = 0.0
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    reasoning: str = ''
    prediction: str = ''
    reversal_zones: List[float] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class Signal:
    id: str = ''
    type: SignalType = SignalType.SCALP
    direction: Direction = Direction.BUY
    entry: float = 0.0
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    risk_reward: float = 0.0
    confidence: int = 0
    timeframe: str = ''
    smc_setup: str = ''
    smc_analysis: Optional[SMCAnalysis] = None
    ai_analyses: List[AIAnalysis] = field(default_factory=list)
    ai_consensus: str = ''
    ai_agreement: int = 0
    analysis_text: str = ''
    prediction: str = ''
    reversal_zones: List[float] = field(default_factory=list)
    status: SignalStatus = SignalStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
