"""
Mustafa Bot - Smart Order Selector Engine
محدد أوامر التداول الذكي (Market Orders vs Pending Limit/Stop Orders)
"""

from typing import Dict, Tuple
from datetime import datetime, timedelta, timezone
from signals.models import OrderType, SignalStatus


class SmartOrderSelector:
    """Institutional Smart Order Selection & Rationale Engine."""

    @staticmethod
    def select_order_type(
        direction: str,
        current_price: float,
        entry_price: float,
        stop_loss: float,
        tp1: float,
        tp2: float,
        tp3: float,
        strategy_name: str,
        signal_type: str,
        exec_analysis: Dict
    ) -> Tuple[OrderType, SignalStatus, str, str, str, str, str]:
        """
        Determines the optimal order type (Market vs Pending Limit/Stop),
        expiration time, holding time, and institutional rationale.
        """
        direction_upper = direction.upper()
        dist_pct = abs(current_price - entry_price) / max(0.0001, current_price)
        is_breakout_strategy = "Breakout" in strategy_name or "Inflection" in strategy_name

        # 1. Determine Order Type & Status
        if dist_pct <= 0.0015:  # Within 0.15% threshold -> Instant execution
            order_type = OrderType.MARKET_BUY if direction_upper == 'BUY' else OrderType.MARKET_SELL
            initial_status = SignalStatus.ACTIVE
            order_badge = "⚡ Instant Market Execution"
        elif is_breakout_strategy:
            if direction_upper == 'BUY' and current_price < entry_price:
                order_type = OrderType.BUY_STOP
            elif direction_upper == 'SELL' and current_price > entry_price:
                order_type = OrderType.SELL_STOP
            else:
                order_type = OrderType.MARKET_BUY if direction_upper == 'BUY' else OrderType.MARKET_SELL

            initial_status = SignalStatus.PENDING if order_type in [OrderType.BUY_STOP, OrderType.SELL_STOP] else SignalStatus.ACTIVE
            order_badge = "🎯 Pending Breakout Stop Order" if initial_status == SignalStatus.PENDING else "⚡ Instant Market Execution"
        else:
            if direction_upper == 'BUY' and current_price > entry_price:
                order_type = OrderType.BUY_LIMIT
            elif direction_upper == 'SELL' and current_price < entry_price:
                order_type = OrderType.SELL_LIMIT
            else:
                order_type = OrderType.MARKET_BUY if direction_upper == 'BUY' else OrderType.MARKET_SELL

            initial_status = SignalStatus.PENDING if order_type in [OrderType.BUY_LIMIT, OrderType.SELL_LIMIT] else SignalStatus.ACTIVE
            order_badge = "📌 Pending Retracement Limit Order" if initial_status == SignalStatus.PENDING else "⚡ Instant Market Execution"

        # 2. Expiration Time & Holding Time
        now = datetime.now(timezone.utc)
        if signal_type == 'SCALP':
            exp_time = (now + timedelta(hours=4)).strftime('%H:%M UTC (%Y-%m-%d)')
            holding_time = "15 - 45 دقيقة (Scalp)"
        else:
            exp_time = (now + timedelta(hours=24)).strftime('%H:%M UTC (%Y-%m-%d)')
            holding_time = "4 - 24 ساعة (Swing)"

        if initial_status == SignalStatus.ACTIVE:
            exp_time = "N/A (نشط حالياً)"

        # 3. Institutional Entry Reason
        if order_type == OrderType.MARKET_BUY:
            entry_reasons = f"تداول شراء فوري لحركة السعر الحالية ({current_price:.2f}) داخل منطقة الطلب المعززة بحجم فوري."
        elif order_type == OrderType.MARKET_SELL:
            entry_reasons = f"تداول بيع فوري لحركة السعر الحالية ({current_price:.2f}) داخل منطقة العرض المعززة بحجم فوري."
        elif order_type == OrderType.BUY_LIMIT:
            entry_reasons = f"أمر شراء معلق ينتظر ارتداد السعر أسفلاً إلى منطقة الطلب وكتلة الأوردر بلوك (Order Block) عند {entry_price:.2f}."
        elif order_type == OrderType.SELL_LIMIT:
            entry_reasons = f"أمر بيع معلق ينتظر ارتداد السعر أعلى إلى منطقة العرض والفجوة السعرية (FVG) عند {entry_price:.2f}."
        elif order_type == OrderType.BUY_STOP:
            entry_reasons = f"أمر شراء معلق يدخل مع انضباط الزخم فور اختراق مستوى المقاومة المحوري عند {entry_price:.2f}."
        else:
            entry_reasons = f"أمر بيع معلق يدخل مع انضباط الزخم فور كسر مستوى الدعم المحوري عند {entry_price:.2f}."

        # 4. Stop Loss Reason
        sl_dist = abs(entry_price - stop_loss)
        if direction_upper == 'BUY':
            sl_reasons = f"موضوع بفاصل أمان أسفل قاع السيولة الهيكلية الهامة عند {stop_loss:.2f} (مسافة المخاطرة: {sl_dist:.2f}$)."
        else:
            sl_reasons = f"موضوع بفاصل أمان أعلى قمة السيولة الهيكلية الهامة عند {stop_loss:.2f} (مسافة المخاطرة: {sl_dist:.2f}$)."

        # 5. Take Profit Targets Reason
        tp_reasons = (
            f"TP1 ({tp1:.2f}): سيولة المنطقة القريبة لحجز الأرباح وتأمين الصفقة.\n"
            f"TP2 ({tp2:.2f}): استهداف مستويات الفجوات السعرية الهيكلية.\n"
            f"TP3 ({tp3:.2f}): استهداف السيولة العالية على الفريمات الأكبر (HTF Pools)."
        )

        return order_type, initial_status, exp_time, holding_time, entry_reasons, sl_reasons, tp_reasons
