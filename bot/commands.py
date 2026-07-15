"""
Mustafa Bot - Telegram Bot Commands
أوامر البوت التفاعلية
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.formatters import MessageFormatter

logger = logging.getLogger('mustafa_bot.bot.commands')


class BotCommands:
    """Handler class for all bot commands."""

    def __init__(self, signal_engine=None):
        self.signal_engine = signal_engine
        self.formatter = MessageFormatter()

    async def start_command(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        welcome = self.formatter.format_welcome()
        await update.message.reply_text(welcome)
        logger.info(f'User {update.effective_user.id} started the bot')

    async def signal_command(self, update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /signal command - run analysis and send signal."""
        await update.message.reply_text('🔄 جاري التحليل... يرجى الانتظار ⏳')

        try:
            if self.signal_engine is None:
                await update.message.reply_text('❌ محرك التحليل غير متوفر')
                return

            # Run both scalp and swing analysis
            signals = await self.signal_engine.run_analysis('SCALP')

            if not signals:
                signals = await self.signal_engine.run_analysis('SWING')

            if signals:
                for signal in signals:
                    msg = self.formatter.format_signal(signal)
                    await update.message.reply_text(msg)
            else:
                await update.message.reply_text(
                    '⚠️ لا توجد إشارات متاحة حالياً\n'
                    'الأسباب المحتملة:\n'
                    '• لم يتم العثور على إعدادات SMC قوية\n'
                    '• لم يتفق نماذج AI على اتجاه واحد\n'
                    '• الإشارات لم تجتز معايير الفلترة\n\n'
                    'سيتم إرسال الإشارات تلقائياً عند توفرها 🔔'
                )

        except Exception as e:
            logger.error(f'Signal command error: {e}', exc_info=True)
            await update.message.reply_text(f'❌ حدث خطأ أثناء التحليل: {str(e)[:100]}')

    async def analysis_command(self, update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /analysis command."""
        await update.message.reply_text('📊 جاري تحليل السوق... ⏳')

        try:
            if self.signal_engine is None:
                await update.message.reply_text('❌ محرك التحليل غير متوفر')
                return

            analysis_msg = await self.signal_engine.get_market_analysis()
            await update.message.reply_text(analysis_msg)

        except Exception as e:
            logger.error(f'Analysis command error: {e}', exc_info=True)
            await update.message.reply_text(f'❌ خطأ في التحليل: {str(e)[:100]}')

    async def predict_command(self, update: Update,
                               context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /predict command."""
        await update.message.reply_text('🔮 جاري حساب التوقعات... ⏳')

        try:
            if self.signal_engine is None:
                await update.message.reply_text('❌ محرك التحليل غير متوفر')
                return

            prediction_msg = await self.signal_engine.get_prediction()
            await update.message.reply_text(prediction_msg)

        except Exception as e:
            logger.error(f'Predict command error: {e}', exc_info=True)
            await update.message.reply_text(f'❌ خطأ في التوقع: {str(e)[:100]}')

    async def status_command(self, update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        try:
            if self.signal_engine:
                active = len(self.signal_engine.active_signals)
                total = self.signal_engine.total_signals
                wins = self.signal_engine.wins
                losses = self.signal_engine.losses
                total_trades = wins + losses
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                from datetime import datetime
                last_update = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            else:
                active, total, win_rate, last_update = 0, 0, 0, 'N/A'

            msg = self.formatter.format_status(active, total, win_rate, last_update)
            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f'Status command error: {e}')
            await update.message.reply_text('❌ خطأ في جلب الحالة')

    async def help_command(self, update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = """📖 المساعدة | Mustafa Bot
━━━━━━━━━━━━━━━━━━━━
📋 الأوامر:

/start - بدء البوت ورسالة الترحيب
/signal - طلب إشارة تداول فورية
/analysis - تحليل شامل لسوق الذهب
/predict - توقع السعر المستقبلي
/status - إحصائيات ومعلومات البوت
/help - عرض هذه الرسالة

📝 ملاحظات:
• البوت يرسل إشارات تلقائية خلال Kill Zones
• كل إشارة تمر بـ 5 مراحل فلترة
• يجب اتفاق 2/3 نماذج AI للإرسال
• الإشارات تشمل دخول + وقف خسارة + 3 أهداف

⚠️ تحذير: التداول ينطوي على مخاطر عالية
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot v1.0"""

        await update.message.reply_text(help_text)
