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

    # ── MetaTrader 5 (MT5) Configuration ──
    MT5_LOGIN: int = int(os.getenv('MT5_LOGIN', 0)) if os.getenv('MT5_LOGIN', '').isdigit() else 0
    MT5_PASSWORD: str = os.getenv('MT5_PASSWORD', '')
    MT5_SERVER: str = os.getenv('MT5_SERVER', '')
    MT5_PATH: str = os.getenv('MT5_PATH', '')
    MT5_AUTO_CONNECT: bool = True

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

    # ── 5 Ultra-Fast Scalping Selectivity Profiles ──
    SELECTIVITY_PROFILES: dict = {
        'SNIPER': {
            'name': '🎯 القناص (Sniper)',
            'min_score': 95,
            'min_rr': 3.0,
            'max_risk_pct': 1.0,
            'description': 'دقة متناهية جداً ومعايير صارمة للغاية (أقل تكرار للصفقات)'
        },
        'CONSERVATIVE': {
            'name': '🛡️ المحافظ (Conservative)',
            'min_score': 90,
            'min_rr': 2.5,
            'max_risk_pct': 1.0,
            'description': 'دقة مؤسساتية عالية مع حماية حذرة لرأس المال'
        },
        'BALANCED': {
            'name': '⚖️ المتوازن (Balanced)',
            'min_score': 82,
            'min_rr': 2.0,
            'max_risk_pct': 1.5,
            'description': 'توازن مثالي بين الدقة وعدد الصفقات المتاحة (النمط الافتراضي)'
        },
        'AGGRESSIVE': {
            'name': '⚡ الهجومي (Aggressive)',
            'min_score': 75,
            'min_rr': 1.5,
            'max_risk_pct': 2.0,
            'description': 'اقتناص محركات الفرص السريعة بمرونة أعلى'
        },
        'ULTRA_AGGRESSIVE': {
            'name': '🚀 الهجومي الفائق (Ultra Aggressive)',
            'min_score': 65,
            'min_rr': 1.2,
            'max_risk_pct': 2.5,
            'description': 'أعلى تكرار ممكن للصفقات وتفاعل فوري مع أدنى حركة'
        }
    }
    DEFAULT_SELECTIVITY: str = 'BALANCED'

    # ── Legacy Trading Profiles Compatibility ──
    TRADING_PROFILES: dict = SELECTIVITY_PROFILES
    DEFAULT_PROFILE: str = DEFAULT_SELECTIVITY

    # ── TradingView Market Price Validation Settings ──
    PRICE_VALIDATION_ENABLED: bool = True
    MAX_DISCREPANCY_PIPS: float = 3.0       # Max allowed pips difference vs TradingView
    MAX_CANDLE_STALE_SECONDS: int = 120    # Max allowed stale candle age in seconds
    MAX_ALLOWED_SPREAD_PIPS: float = 10.0   # Max allowed spread pips

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
