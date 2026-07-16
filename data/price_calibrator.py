"""
Mustafa Bot - Broker Price Calibration System
نظام المعايرة التفاعلي لمطابقة أسعار البوت مع أسعار منصة الوسيط (JustMarkets / ICMarkets / Exness) بدقة 100%
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger('mustafa_bot.data.price_calibrator')


class BrokerPriceCalibrator:
    """Manages custom price offsets per user session to ensure 100% price synchronization with broker app."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrokerPriceCalibrator, cls).__new__(cls)
            cls._instance.user_offsets: Dict[int, Dict[str, float]] = {}
        return cls._instance

    def set_user_offset(self, chat_id: int, symbol_key: str, offset: float) -> None:
        """Set manual or calibrated price offset for a specific symbol."""
        if chat_id not in self.user_offsets:
            self.user_offsets[chat_id] = {}
        self.user_offsets[chat_id][symbol_key] = round(offset, 4)
        logger.info(f"🎯 Calibrated broker price offset for chat_id={chat_id}, symbol={symbol_key}: {offset:+.4f}")

    def get_user_offset(self, chat_id: int, symbol_key: str) -> float:
        """Get calibrated price offset for a specific symbol."""
        return self.user_offsets.get(chat_id, {}).get(symbol_key, 0.0)

    def apply_offset(self, raw_price: float, chat_id: int, symbol_key: str) -> float:
        """Apply calibrated offset to raw market price."""
        if not raw_price or raw_price <= 0:
            return raw_price
        offset = self.get_user_offset(chat_id, symbol_key)
        return round(raw_price + offset, 4)

    def reset_user_offset(self, chat_id: int, symbol_key: Optional[str] = None) -> None:
        """Reset custom price offset back to default."""
        if chat_id in self.user_offsets:
            if symbol_key:
                self.user_offsets[chat_id].pop(symbol_key, None)
            else:
                self.user_offsets.pop(chat_id, None)
