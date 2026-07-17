"""
Mustafa Bot - Message Formatter
تنسيق رسائل الإشارات والتوصيات بشكل مبسط ونظيف
"""

from signals.models import Signal, SignalType, Direction
from datetime import datetime, timedelta
from typing import Dict, List


class MessageFormatter:
    """Formats signals into clean, clear Telegram messages."""

    @staticmethod
    def format_signal(signal: Signal) -> str:
        """Format a clean, ultra-focused signal message with symbol, order type, win rate, entry, SL, and TPs."""
        sym = getattr(signal, 'symbol', 'XAU/USD')
        decimals = 5 if ('EUR/USD' in sym or 'GBP/USD' in sym) else 3 if 'USD/JPY' in sym else 2
        price_fmt = f",.{decimals}f"

        order_type_str = getattr(signal.order_type, 'value', str(signal.order_type)) if hasattr(signal, 'order_type') else ('BUY' if signal.direction == Direction.BUY else 'SELL')
        if 'LIMIT' in order_type_str:
            order_badge = f"📌 {order_type_str}"
        elif 'STOP' in order_type_str:
            order_badge = f"🎯 {order_type_str}"
        else:
            order_badge = f"⚡ {order_type_str}"

        conf_pct = getattr(signal, 'confidence', 80)

        msg = f"""🌐 *{sym}*
━━━━━━━━━━━━━━━━━━━━
📈 *نوع الأمر*: `{order_badge}`
🔥 *نسبة نجاح الصفقة*: `{conf_pct}%`
💰 *منطقة الدخول*: `{signal.entry:{price_fmt}}`
🛑 *وقف الخسارة*: `{signal.stop_loss:{price_fmt}}`
🎯 *الهدف الأول*: `{signal.take_profit_1:{price_fmt}}`
🎯 *الهدف الثاني*: `{signal.take_profit_2:{price_fmt}}`
🎯 *الهدف الثالث*: `{signal.take_profit_3:{price_fmt}}`"""

        return msg

    @staticmethod
    def format_institutional_signal(setup: dict) -> str:
        """Format a clean, ultra-focused signal message with symbol, order type, win rate, entry, SL, and TPs."""
        symbol = setup.get('symbol', 'XAU/USD')
        decimals = 5 if ('EUR/USD' in symbol or 'GBP/USD' in symbol) else 3 if 'USD/JPY' in symbol else 2
        price_fmt = f",.{decimals}f"
        
        entry_str = f"{setup.get('entry', 0.0):{price_fmt}}"
        sl_str = f"{setup.get('stop_loss', 0.0):{price_fmt}}"
        tp1_str = f"{setup.get('tp1', 0.0):{price_fmt}}"
        tp2_str = f"{setup.get('tp2', 0.0):{price_fmt}}"
        tp3_str = f"{setup.get('tp3', 0.0):{price_fmt}}"

        order_type_str = setup.get('order_type_str', 'MARKET_BUY' if setup.get('direction') == 'BUY' else 'MARKET_SELL')
        if 'LIMIT' in order_type_str:
            order_badge = f"📌 {order_type_str}"
        elif 'STOP' in order_type_str:
            order_badge = f"🎯 {order_type_str}"
        else:
            order_badge = f"⚡ {order_type_str}"

        conf_pct = setup.get('score', setup.get('confidence', 80))

        msg = f"""🌐 *{symbol}*
━━━━━━━━━━━━━━━━━━━━
📈 *نوع الأمر*: `{order_badge}`
🔥 *نسبة نجاح الصفقة*: `{conf_pct}%`
💰 *منطقة الدخول*: `{entry_str}`
🛑 *وقف الخسارة*: `{sl_str}`
🎯 *الهدف الأول*: `{tp1_str}`
🎯 *الهدف الثاني*: `{tp2_str}`
🎯 *الهدف الثالث*: `{tp3_str}`"""

        return msg

    @staticmethod
    def format_analysis(analysis_text: str, current_price: float, trend: str) -> str:
        """Format a market analysis message."""
        trend_map = {'BULLISH': 'صاعد 📈', 'BEARISH': 'هابط 📉', 'NEUTRAL': 'محايد ↔️'}
        trend_text = trend_map.get(trend, 'محايد ↔️')
        mecca_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M:%S %p')

        msg = f"""📊 *تحليل السوق | MUSTAFA BOT*
━━━━━━━━━━━━━━━━━━━━
💰 السعر الحالي: `{current_price:,.2f}`
⏰ التاريخ والوقت: {mecca_time} بتوقيت مكة
📈 الاتجاه: {trend_text}
━━━━━━━━━━━━━━━━━━━━
{analysis_text}
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot | SMC + ICT"""
        return msg

    @staticmethod
    def format_prediction(prediction: str, reversal_zones: list) -> str:
        """Format a price prediction message."""
        zones_text = '\n'.join([f'  📍 {z:,.2f}' for z in reversal_zones[:5]]) if reversal_zones else '  غير متاح'
        mecca_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M:%S %p')

        msg = f"""🔮 *توقعات التداول | MUSTAFA BOT*
━━━━━━━━━━━━━━━━━━━━
⏰ التاريخ والوقت: {mecca_time} بتوقيت مكة
━━━━━━━━━━━━━━━━━━━━
{prediction if prediction else 'لا يوجد توقع متاح حالياً'}
━━━━━━━━━━━━━━━━━━━━
📍 مناطق الارتداد القوية:
{zones_text}
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot"""
        return msg

    @staticmethod
    def format_welcome() -> str:
        """Format welcome message for /start command."""
        from database.db_manager import DatabaseManager
        db_msg = DatabaseManager().get_template('welcome_message')
        if db_msg:
            return db_msg

        msg = """━━━━━━━━━━━━━━━━━━━━
💎 بوت التداول والتحليل المؤسساتي (SMC + ICT)

📥 استخدم الأزرار بالأسفل لاستعراض التوصيات والتحليلات الفورية.
━━━━━━━━━━━━━━━━━━━━"""
        return msg

    @staticmethod
    def format_status(active_signals: int, total_signals: int, win_rate: float, last_update: str) -> str:
        """Format bot status message."""
        msg = f"""📊 *حالة البوت والأداء*
━━━━━━━━━━━━━━━━━━━━
✅ الحالة: نشط ومتصل 🟢
📡 آخر تحديث: {last_update}
📈 إشارات نشطة: {active_signals} | إجمالي الإشارات: {total_signals}
🏆 نسبة النجاح: {win_rate:.1f}%
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot Institutional Engine"""
        return msg

    @staticmethod
    def format_dashboard_status(symbol: str, profile_name: str, active_trades_count: int, data_feed_status: str, last_analysis_time: str, active_session: str) -> str:
        """Format dashboard summary status text."""
        msg = f"""🖥️ *لوحة التحكم الفورية*
━━━━━━━━━━━━━━━━━━━━
🌐 الرمز النشط: *{symbol}*
🎯 الصفقات الفعالة: *{active_trades_count} صفقات*
📡 تغذية الأسعار: *{data_feed_status}*
⏰ آخر فحص: *{last_analysis_time}*
🏛️ جلسة التداول: *{active_session}*
━━━━━━━━━━━━━━━━━━━━"""
        return msg

    @staticmethod
    def format_trade_history(trades: list) -> str:
        """Format history list of past trades."""
        if not trades:
            return "📋 *سجل الصفقات*: لا توجد صفقات منفذة سابقة في السجل حالياً."

        lines = ["📋 *سجل الصفقات السابقة الأخيرة*:\n━━━━━━━━━━━━━━━━━━━━"]
        for t in trades[:10]:
            dir_icon = '🟢 BUY' if t['direction'] == 'BUY' else '🔴 SELL'
            status_icon = '✅ TP' if 'TP' in t['status'] else '🛑 SL' if t['status'] == 'SL_HIT' else '⏳ WAITING'
            lines.append(f"• *{t['symbol']}* ({t['timeframe']}) | {dir_icon} @ `{t['entry']}` ➔ {t['status']} ({status_icon})")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    @staticmethod
    def format_daily_summary(signals_today: int, wins: int, losses: int) -> str:
        """Format daily summary message."""
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        msg = f"""📋 *ملخص اليوم*
━━━━━━━━━━━━━━━━━━━━
📊 إشارات اليوم: {signals_today} | ✅ ناجحة: {wins} | ❌ خاسرة: {losses}
📈 نسبة النجاح: {win_rate:.1f}%
━━━━━━━━━━━━━━━━━━━━"""
        return msg
