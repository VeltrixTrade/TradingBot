"""
Mustafa Bot - Centralized Configuration
يحمل جميع الإعدادات من متغيرات البيئة وملف symbols.json
"""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger('mustafa_bot.config')


class Config:
    """Centralized configuration for Mustafa Bot."""

    # ── Telegram ──
    TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '') or os.getenv('TELEGRAM_CHANNEL_ID', '')

    # ── Dynamic Symbol Configuration ──
    SYMBOLS_FILE_PATH: str = os.path.join(os.path.dirname(__file__), 'symbols.json')
    SUPPORTED_SYMBOLS: dict = {}

    @classmethod
    def load_symbols(cls) -> dict:
        """Load symbols dynamically from symbols.json."""
        if os.path.exists(cls.SYMBOLS_FILE_PATH):
            try:
                with open(cls.SYMBOLS_FILE_PATH, 'r', encoding='utf-8') as f:
                    cls.SUPPORTED_SYMBOLS = json.load(f)
                    logger.info(f"Loaded {len(cls.SUPPORTED_SYMBOLS)} symbols from symbols.json")
                    return cls.SUPPORTED_SYMBOLS
            except Exception as e:
                logger.error(f"Failed to load symbols.json: {e}")
        
        # Fallback default dict
        cls.SUPPORTED_SYMBOLS = {
            'XAU/USD': {
                'symbol_id': 'XAU/USD',
                'display': '🟡 XAU/USD (Gold)',
                'category': 'COMMODITY',
                'yfinance_symbol': 'GC=F',
                'binance_symbol': 'PAXGUSDT',
                'tradingview_symbol': 'XAUUSD',
                'tradingview_exchange': 'OANDA',
                'pip_multiplier': 0.1,
                'default_spread': 0.3,
                'decimal_places': 2
            }
        }
        return cls.SUPPORTED_SYMBOLS

    # ── AI API Keys ──
    DEEPSEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY', '')
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')

    # ── AI Model Names ──
    DEEPSEEK_MODEL: str = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    # ── Trading & Timeframes ──
    SYMBOL: str = 'XAUUSD'
    EXCHANGE: str = 'OANDA'
    SCALP_TIMEFRAMES: list = ['1m', '5m', '15m']
    SWING_TIMEFRAMES: list = ['30m', '1h', '4h']

    # ── Dual Trading Profiles ──
    TRADING_PROFILES: dict = {
        'CONSERVATIVE': {
            'name': '🛡️ المحافظ (Conservative)',
            'min_score': 90,
            'min_rr_scalp': 2.0,
            'min_rr_swing': 3.0,
            'max_risk_pct': 1.0,
            'require_strict_htf': True
        },
        'AGGRESSIVE': {
            'name': '⚡ الهجومي (Aggressive)',
            'min_score': 75,
            'min_rr_scalp': 1.5,
            'min_rr_swing': 2.0,
            'max_risk_pct': 2.0,
            'require_strict_htf': False
        }
    }
    DEFAULT_PROFILE: str = 'CONSERVATIVE'

    # ── Risk Management ──
    MIN_RISK_REWARD_SCALP: float = 2.0
    MIN_RISK_REWARD_SWING: float = 3.0
    MIN_CONFIDENCE: int = 75
    MAX_DAILY_SCALP_SIGNALS: int = 5
    MAX_DAILY_SWING_SIGNALS: int = 2

    # ── AI Consensus ──
    MIN_AI_AGREEMENT: int = 2  # out of 3

    # ── Scheduler ──
    ANALYSIS_INTERVAL_SECONDS: int = 60
    PRICE_UPDATE_INTERVAL: int = 30

    # ── Kill Zones (UTC hours) ──
    KILL_ZONES: dict = {
        'london': {'start': 8, 'end': 12},
        'new_york': {'start': 13, 'end': 17},
        'asian': {'start': 0, 'end': 3},
    }

    @classmethod
    def validate(cls) -> list:
        """Validate that all required config values are set."""
        errors = []
        if not cls.TELEGRAM_TOKEN:
            errors.append('TELEGRAM_BOT_TOKEN is required')
        if not cls.CHAT_ID:
            errors.append('TELEGRAM_CHAT_ID is required')
        if not cls.DEEPSEEK_API_KEY:
            errors.append('DEEPSEEK_API_KEY is required')
        if not cls.GEMINI_API_KEY:
            errors.append('GEMINI_API_KEY is required')
        if not cls.OPENAI_API_KEY:
            errors.append('OPENAI_API_KEY is required')
        return errors


# Load symbols at startup
Config.load_symbols()
