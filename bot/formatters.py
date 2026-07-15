"""
Mustafa Bot - Message Formatter
تنسيق رسائل الإشارات بشكل احترافي مع إيموجي
"""

from signals.models import Signal, SignalType, Direction
from datetime import datetime


class MessageFormatter:
    """Formats signals into beautiful Telegram messages."""

    @staticmethod
    def format_signal(signal: Signal) -> str:
        """Format a signal into a beautiful Telegram message."""
        # Direction
        if signal.direction == Direction.BUY:
            dir_emoji = '🟢'
            dir_text = 'شراء'
            sl_diff = signal.entry - signal.stop_loss
            tp1_diff = signal.take_profit_1 - signal.entry
            tp2_diff = signal.take_profit_2 - signal.entry
            tp3_diff = signal.take_profit_3 - signal.entry
        else:
            dir_emoji = '🔴'
            dir_text = 'بيع'
            sl_diff = signal.stop_loss - signal.entry
            tp1_diff = signal.entry - signal.take_profit_1
            tp2_diff = signal.entry - signal.take_profit_2
            tp3_diff = signal.entry - signal.take_profit_3

        # Signal type
        type_text = 'سكالب ⚡' if signal.type == SignalType.SCALP else 'سوينغ 🌊'

        # Confidence stars
        if signal.confidence >= 90:
            conf_stars = '⭐⭐⭐⭐⭐'
        elif signal.confidence >= 80:
            conf_stars = '⭐⭐⭐⭐'
        elif signal.confidence >= 70:
            conf_stars = '⭐⭐⭐'
        else:
            conf_stars = '⭐⭐'

        # Reversal zones
        zones_text = ' | '.join([f'{z:.2f}' for z in signal.reversal_zones[:5]]) if signal.reversal_zones else 'غير متاح'

        from datetime import datetime, timedelta
        mecca_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M:%S %p')

        msg = f"""🔔 إشارة ذهب جديدة | MUSTAFA BOT
━━━━━━━━━━━━━━━━━━━━
⏰ التاريخ والوقت: {mecca_time} بتوقيت مكة المكرمة
📊 النوع: {type_text} | {dir_text} {dir_emoji}
⏰ الإطار الزمني: {signal.timeframe}
━━━━━━━━━━━━━━━━━━━━
💰 سعر الدخول: {signal.entry:,.2f}
🛑 وقف الخسارة: {signal.stop_loss:,.2f} ({sl_diff:+.2f}$)
🎯 الهدف 1: {signal.take_profit_1:,.2f} ({tp1_diff:+.2f}$)
🎯 الهدف 2: {signal.take_profit_2:,.2f} ({tp2_diff:+.2f}$)
🎯 الهدف 3: {signal.take_profit_3:,.2f} ({tp3_diff:+.2f}$)
━━━━━━━━━━━━━━━━━━━━
📈 المخاطرة/العائد: 1:{signal.risk_reward:.1f}
🤖 ثقة AI: {signal.confidence}% ({signal.ai_agreement}/3 إجماع)
{conf_stars}
🏛️ إعداد SMC: {signal.smc_setup}
━━━━━━━━━━━━━━━━━━━━
📝 التحليل:
{signal.analysis_text[:400]}

🔮 التوقع: {signal.prediction[:200] if signal.prediction else 'غير متاح'}
📍 مناطق الارتداد: {zones_text}
━━━━━━━━━━━━━━━━━━━━
⚠️ إخلاء مسؤولية: ليست نصيحة مالية
🤖 Mustafa Bot | SMC + ICT + AI"""

        return msg

    @staticmethod
    def format_analysis(analysis_text: str, current_price: float,
                          trend: str) -> str:
        """Format a market analysis message."""
        trend_map = {'BULLISH': 'صاعد 📈', 'BEARISH': 'هابط 📉', 'NEUTRAL': 'محايد ↔️'}
        trend_text = trend_map.get(trend, 'محايد ↔️')

        from datetime import datetime, timedelta
        mecca_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M:%S %p')

        msg = f"""📊 تحليل سوق الذهب | MUSTAFA BOT
━━━━━━━━━━━━━━━━━━━━
💰 السعر الحالي: {current_price:,.2f}
⏰ التاريخ والوقت: {mecca_time} بتوقيت مكة المكرمة
📈 الاتجاه: {trend_text}
━━━━━━━━━━━━━━━━━━━━
{analysis_text}
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot | تحليل SMC + ICT + AI"""

        return msg

    @staticmethod
    def format_prediction(prediction: str, reversal_zones: list) -> str:
        """Format a price prediction message."""
        zones_text = '\n'.join([f'  📍 {z:,.2f}' for z in reversal_zones[:5]]) if reversal_zones else '  غير متاح'

        from datetime import datetime, timedelta
        mecca_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M:%S %p')

        msg = f"""🔮 توقعات الذهب | MUSTAFA BOT
━━━━━━━━━━━━━━━━━━━━
⏰ التاريخ والوقت: {mecca_time} بتوقيت مكة المكرمة
━━━━━━━━━━━━━━━━━━━━
{prediction if prediction else 'لا يوجد توقع متاح حالياً'}
━━━━━━━━━━━━━━━━━━━━
📍 مناطق الارتداد القوية:
{zones_text}
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot | توقعات AI"""

        return msg

    @staticmethod
    def format_welcome() -> str:
        """Format welcome message for /start command."""
        msg = """🤖 مرحباً بك في Mustafa Bot!
━━━━━━━━━━━━━━━━━━━━
💎 بوت إشارات الذهب بالذكاء الاصطناعي

⚙️ التقنيات المستخدمة:
  🏛️ استراتيجية SMC + ICT
  🧠 3 نماذج AI: DeepSeek + Gemini + ChatGPT
  📊 بيانات حية من TradingView
  🔍 فلترة 5 مراحل للإشارات

📥 يرجى استخدام الأزرار التفاعلية بالأسفل للتحكم بالبوت وطلب التحليلات والتوقعات.

🔔 يتم إرسال الإشارات تلقائياً خلال ساعات التداول النشطة (Kill Zones).
━━━━━━━━━━━━━━━━━━━━
⚠️ تنبيه: الإشارات ليست نصيحة مالية
🤖 Mustafa Bot v1.0"""

        return msg


    @staticmethod
    def format_status(active_signals: int, total_signals: int,
                       win_rate: float, last_update: str) -> str:
        """Format bot status message."""
        msg = f"""📊 حالة Mustafa Bot
━━━━━━━━━━━━━━━━━━━━
✅ الحالة: نشط ومتصل
📡 آخر تحديث: {last_update}

📈 الإحصائيات:
  🔹 إشارات نشطة: {active_signals}
  🔹 إجمالي الإشارات: {total_signals}
  🔹 نسبة النجاح: {win_rate:.1f}%

⚙️ النظام:
  🧠 AI: DeepSeek ✅ | Gemini ✅ | ChatGPT ✅
  📊 البيانات: TradingView ✅
  🔍 الفلتر: 5 مراحل ✅
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot | SMC + ICT + AI"""

        return msg

    @staticmethod
    def format_daily_summary(signals_today: int, wins: int, losses: int) -> str:
        """Format daily summary message."""
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        msg = f"""📋 ملخص اليوم | MUSTAFA BOT
━━━━━━━━━━━━━━━━━━━━
📊 إشارات اليوم: {signals_today}
✅ ناجحة: {wins}
❌ خاسرة: {losses}
📈 نسبة النجاح: {win_rate:.1f}%
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot | التقرير اليومي"""

        return msg
