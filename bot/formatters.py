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
        # Institutional report override
        if signal.analysis_text and "تقرير الإشارة المؤسساتي" in signal.analysis_text:
            return signal.analysis_text

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
    def format_dashboard_status(
        symbol: str,
        profile_name: str,
        active_trades_count: int,
        data_feed_status: str,
        last_analysis_time: str,
        active_session: str
    ) -> str:
        """Format dashboard summary status text."""
        msg = f"""🖥️ *لوحة التحكم الفورية (Real-Time Status Dashboard)*
━━━━━━━━━━━━━━━━━━━━
🌐 الرمز النشط: *{symbol}*
🛡️ النمط المفعل: *{profile_name}*
🎯 الصفقات الفعالة: *{active_trades_count} صفقات*
📡 حالة تغذية الأسعار: *{data_feed_status}*
⏰ وقت آخر فحص: *{last_analysis_time}*
🏛️ جلسة التداول الحالية: *{active_session}*
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot Institutional Platform v2.5"""
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
            lines.append(
                f"• *{t['symbol']}* ({t['timeframe']}) | {dir_icon} @ `{t['entry']}` ➔ Status: *{t['status']}* ({status_icon})"
            )
        lines.append("━━━━━━━━━━━━━━━━━━━━\n🤖 Mustafa Bot Persistence Log")
        return "\n".join(lines)

    @staticmethod
    def format_institutional_signal(setup: dict) -> str:
        """Format an institutional trade setup into a highly structured report."""
        dir_emoji = '🟢 BUY' if setup['direction'] == 'BUY' else '🔴 SELL'
        
        from datetime import datetime, timedelta
        mecca_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M:%S %p')

        # Determine dynamic decimals based on symbol
        symbol = setup.get('symbol', 'XAU/USD')
        decimals = 5 if ('EUR/USD' in symbol or 'GBP/USD' in symbol) else 3 if 'USD/JPY' in symbol else 2
        price_fmt = f",.{decimals}f"
        
        entry_str = f"{setup.get('entry', 0.0):{price_fmt}}"
        sl_str = f"{setup.get('stop_loss', 0.0):{price_fmt}}"
        tp1_str = f"{setup.get('tp1', 0.0):{price_fmt}}"
        tp2_str = f"{setup.get('tp2', 0.0):{price_fmt}}"
        tp3_str = f"{setup.get('tp3', 0.0):{price_fmt}}"

        # Formulate status bars
        def make_progress_bar(percentage: int, total_chars: int = 10, fill_char: str = '🔥', empty_char: str = '⬜') -> str:
            filled = int(round((percentage / 100) * total_chars))
            filled = min(total_chars, max(0, filled))
            return (fill_char * filled) + (empty_char * (total_chars - filled))

        score = setup.get('score', 80)
        score_bar = make_progress_bar(score, 10, '🔥', '⬜')

        # Format Order Blocks list
        ob_text = "\n".join([f"  • {ob}" for ob in setup.get('order_blocks', [])]) if setup.get('order_blocks') else "  • No active OB found"
        # Format Breaker Blocks
        bb_text = "\n".join([f"  • {bb}" for bb in setup.get('breaker_blocks', [])]) if setup.get('breaker_blocks') else "  • No active Breakers"
        # Format FVGs
        fvg_text = "\n".join([f"  • {fvg}" for fvg in setup.get('fvgs', [])]) if setup.get('fvgs') else "  • No open FVG"

        from data.mt5_connection import MT5ConnectionManager
        td_info = MT5ConnectionManager().get_symbol_info(symbol)
        td_bid_ask = f"Bid: {td_info['bid']:{price_fmt}} | Ask: {td_info['ask']:{price_fmt}} | Spread: {td_info['spread_pips']} pips" if td_info else "TwelveData Feed Synchronized"

        rank_score_str = f" | التقييم: {score}/100"
        strategy_title = setup.get('strategy_name', 'SMC + ICT Institutional Strategy')

        msg = f"""⚡ *إشارة تداول فورية | TwelveData Live Data*
━━━━━━━━━━━━━━━━━━━━
⏰ تاريخ التقرير: {mecca_time} بتوقيت مكة المكرمة{rank_score_str}
📡 المصدر: TwelveData Real-Time API

Symbol: {symbol}
Trade Type: {dir_emoji}
Entry: {entry_str}
Stop Loss: {sl_str}
Take Profit 1: {tp1_str}
Take Profit 2: {tp2_str}
Risk-to-Reward: 1:{setup.get('risk_reward', 2.0):.1f}
Confidence Score: {score}/100
Timeframe: {setup.get('timeframe_name', 'M15')}
Live Ticks: {td_bid_ask}
Strategy Module: {strategy_title}
Reason for Entry: {setup.get('reasons_entry', 'Structure alignment')}

━━━━━━━━━━━━━━━━━━━━
📊 معطيات التحليل والهيكل:
  • اتجاه السوق (Bias): {setup.get('market_bias', 'NEUTRAL')}
  • الاتجاه الحالي (Trend): {setup.get('trend_direction', 'NEUTRAL')}
  • هيكل السوق (Market Structure): {setup.get('structure_analysis', 'Balanced')}
  • تأكيد الكسر (BOS): {'مؤكد ✅' if setup.get('bos_confirmed') else 'غير متوفر ❌'}
  • تغير الشخصية (CHOCH): {'مؤكد ✅' if setup.get('choch_confirmed') else 'غير متوفر ❌'}

🏛️ الكتل السعرية والفجوات (SMC/ICT Zones):
  • مناطق الأوردر بلوك (Order Blocks):
{ob_text}
  • كتل الاختراق (Breaker Blocks):
{bb_text}
  • فجوات القيمة العادلة (FVGs):
{fvg_text}
  • مستويات السيولة (Liquidity Pools):
  • {setup.get('liquidity_zones', 'No major liquidity pool swept')}
  • المنطقة السعرية (Premium/Discount): {setup.get('premium_discount', 'Discount Zone')}

📐 تأكيدات الدخول والزخم:
  • تأكيد السيولة المؤسساتية: {setup.get('institutional_confirmation', 'Neutral')}
  • فحص الزخم (Momentum): {setup.get('momentum_analysis', 'Neutral')}
  • جلسة التداول النشطة: {setup.get('session_analysis', 'All Session')}
  • معدل التذبذب والسيولة: {setup.get('volatility_analysis', 'N/A')}

⚡ درجة جودة الصفقة (Quality Score): {score}/100
  [{score_bar}]
🧠 نسبة الثقة: {setup.get('confidence', 80)}%
🛡️ مستوى إدارة المخاطر: {setup.get('risk_pct', '1.0%')}

📝 المنطق والتبرير الفني للدخول:
{setup.get('reasoning', 'Aligned with institutional order flow.')}
━━━━━━━━━━━━━━━━━━━━
⚠️ إخلاء مسؤولية: تداول العملات والمعادن محاط بمخاطر عالية. ليست نصيحة استثمارية.
🤖 MUSTAFA BOT | MULTI-SYMBOL ENGINE"""
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
