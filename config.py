"""
Mustafa Bot - Centralized Configuration
يحمل جميع الإعدادات من متغيرات البيئة
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Centralized configuration for Mustafa Bot."""

    # ── Telegram ──
    TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '') or os.getenv('TELEGRAM_CHANNEL_ID', '')

    # ── Supported Instruments ──
    SUPPORTED_SYMBOLS: dict = {
        'XAU/USD': {
            'display': '🟡 XAU/USD (Gold)',
            'yfinance_symbol': 'GC=F',
            'binance_symbol': 'PAXGUSDT',
            'tradingview_symbol': 'XAUUSD',
            'tradingview_exchange': 'OANDA',
            'pip_multiplier': 0.1,
            'default_spread': 0.3,
            'decimal_places': 2
        },
        'EUR/USD': {
            'display': '🔵 EUR/USD',
            'yfinance_symbol': 'EURUSD=X',
            'binance_symbol': 'EURUSDT',
            'tradingview_symbol': 'EURUSD',
            'tradingview_exchange': 'FX_IDC',
            'pip_multiplier': 0.0001,
            'default_spread': 0.00015,
            'decimal_places': 5
        },
        'GBP/USD': {
            'display': '🟢 GBP/USD',
            'yfinance_symbol': 'GBPUSD=X',
            'binance_symbol': 'GBPUSDT',
            'tradingview_symbol': 'GBPUSD',
            'tradingview_exchange': 'FX_IDC',
            'pip_multiplier': 0.0001,
            'default_spread': 0.0002,
            'decimal_places': 5
        },
        'USD/JPY': {
            'display': '🟣 USD/JPY',
            'yfinance_symbol': 'USDJPY=X',
            'binance_symbol': 'USDJPY',
            'tradingview_symbol': 'USDJPY',
            'tradingview_exchange': 'FX_IDC',
            'pip_multiplier': 0.01,
            'default_spread': 0.015,
            'decimal_places': 3
        }
    }


    # ── AI API Keys ──
    DEEPSEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY', '')
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')

    # ── AI Model Names ──
    DEEPSEEK_MODEL: str = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    # ── Trading ──
    SYMBOL: str = 'XAUUSD'
    EXCHANGE: str = 'OANDA'
    SCALP_TIMEFRAMES: list = ['1m', '5m', '15m']
    SWING_TIMEFRAMES: list = ['30m', '1h', '4h']

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
