"""
Mustafa Bot - Telegram Bot Commands
أوامر البوت التفاعلية
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


from bot.formatters import MessageFormatter

logger = logging.getLogger('mustafa_bot.bot.commands')


class BotCommands:
    """Handler class for all bot commands."""

    def __init__(self, signal_engine=None):
        self.signal_engine = signal_engine
        self.formatter = MessageFormatter()
        self.user_states = {}

    async def start_command(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user_id = update.effective_user.id
        self.user_states[user_id] = 'normal'  # Reset state

        welcome = self.formatter.format_welcome()
        keyboard = [
            ['🔔 طلب إشارة فورية', '📊 تحليل الذهب'],
            ['🔮 توقع السعر المستقبلي', '⚙️ حالة البوت والاحصائيات'],
            ['💬 التحدث مع الذكاء الاصطناعي']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(welcome, reply_markup=reply_markup)
        logger.info(f'User {user_id} started the bot')



    async def signal_command(self, update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /signal command - run analysis and send signal."""
        await update.message.reply_text('🔄 جاري التحليل... يرجى الانتظار ⏳')

        try:
            if self.signal_engine is None:
                await update.message.reply_text('❌ محرك التحليل غير متوفر')
                return

            # Run both scalp and swing analysis with is_manual=True
            signals = await self.signal_engine.run_analysis('SCALP', is_manual=True)

            if not signals:
                signals = await self.signal_engine.run_analysis('SWING', is_manual=True)

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
📋 الأوامر المتاحة من لوحة الأزرار:

• 🔔 طلب إشارة فورية - اختيار إشارة سكالب أو سوينغ للذهب
• 📊 تحليل الذهب - تحليل فني مفصل لهيكل السوق والـ Order Blocks
• 🔮 توقع السعر المستقبلي - التوقعات السعرية ومناطق الارتداد
• ⚙️ حالة البوت والاحصائيات - إحصائيات البوت ونسبة النجاح
• 💬 التحدث مع الذكاء الاصطناعي - محادثة تفاعلية مع مستشار الذهب

📝 ملاحظات:
• يتم إرسال الإشارات تلقائياً خلال ساعات التداول النشطة
• للتراجع أو الخروج من أي وضع، أرسل /cancel

⚠️ تحذير: التداول ينطوي على مخاطر عالية
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot v1.0"""

        keyboard = [
            ['🔔 طلب إشارة فورية', '📊 تحليل الذهب'],
            ['🔮 توقع السعر المستقبلي', '⚙️ حالة البوت والاحصائيات'],
            ['💬 التحدث مع الذكاء الاصطناعي']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(help_text, reply_markup=reply_markup)

    async def cancel_command(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command - exit chat mode."""
        user_id = update.effective_user.id
        self.user_states[user_id] = 'normal'
        await update.message.reply_text('🔙 تم الخروج من وضع التحدث مع الذكاء الاصطناعي والعودة للوضع الطبيعي.')

    async def handle_message(self, update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages to route button clicks and AI chat."""
        text = update.message.text
        user_id = update.effective_user.id
        current_state = self.user_states.get(user_id, 'normal')

        # Check for main menu button clicks to exit chat mode automatically
        if text in ['🔔 طلب إشارة فورية', '📊 تحليل الذهب', '🔮 توقع السعر المستقبلي', '⚙️ حالة البوت والاحصائيات', '💬 التحدث مع الذكاء الاصطناعي']:
            self.user_states[user_id] = 'normal'
            current_state = 'normal'

        if current_state == 'chat':
            # User is in chat mode, forward message to AI
            await update.message.reply_text('🤔 جاري تفكير المستشار الذكي... ⏳')
            try:
                ai_response = await self.signal_engine.ai_manager.get_chat_response(text)
                await update.message.reply_text(ai_response)
            except Exception as e:
                logger.error(f'AI Chat error: {e}')
                await update.message.reply_text('❌ حدث خطأ أثناء معالجة رسالتك بالذكاء الاصطناعي.')
            return

        # Normal mode button routing
        if text == '🔔 طلب إشارة فورية':
            keyboard = [
                [
                    InlineKeyboardButton("⚡ إشارة سكالب (Scalp)", callback_data="get_scalp"),
                    InlineKeyboardButton("🌊 إشارة سوينغ (Swing)", callback_data="get_swing")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📥 اختر نوع إشارة تداول الذهب المطلوبة:", reply_markup=reply_markup)

        elif text == '📊 تحليل الذهب':
            await self.analysis_command(update, context)

        elif text == '🔮 توقع السعر المستقبلي':
            await self.predict_command(update, context)

        elif text == '⚙️ حالة البوت والاحصائيات':
            await self.status_command(update, context)

        elif text == '💬 التحدث مع الذكاء الاصطناعي':
            self.user_states[user_id] = 'chat'
            chat_welcome = (
                "💬 لقد دخلت الآن وضع التحدث مع الذكاء الاصطناعي 🧠 (مستشار تداول الذهب الخاص بك).\n\n"
                "اكتب أي سؤال بخصوص الذهب، التحليل الفني، إدارة المخاطر، أو سلوك السوق، وسأجيبك فوراً كمتداول خبير لأكثر من 20 سنة!\n\n"
                "*(للخروج والعودة للوحة الأزرار، اضغط على أي زر آخر أو أرسل /cancel)*"
            )
            await update.message.reply_text(chat_welcome, parse_mode="Markdown")

    async def handle_callback(self, update: Update,
                               context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button clicks for signals."""
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "get_scalp":
            await query.message.reply_text("🔄 جاري تحليل الذهب لإشارات السكالب (Scalp) عبر SMC + AI... ⏳")
            try:
                signals = await self.signal_engine.run_analysis('SCALP', is_manual=True)
                if signals:
                    for signal in signals:
                        msg = self.formatter.format_signal(signal)
                        await query.message.reply_text(msg)
                else:
                    await query.message.reply_text("⚠️ لم يتم العثور على إشارة سكالب تتوافق مع شروط الفلترة وAI حالياً.\nسيتم الإرسال تلقائياً فور توفرها.")
            except Exception as e:
                logger.error(f"Callback Scalp error: {e}")
                await query.message.reply_text("❌ حدث خطأ أثناء تحليل السكالب.")

        elif data == "get_swing":
            await query.message.reply_text("🔄 جاري تحليل الذهب لإشارات السوينغ (Swing) عبر SMC + AI... ⏳")
            try:
                signals = await self.signal_engine.run_analysis('SWING', is_manual=True)
                if signals:
                    for signal in signals:
                        msg = self.formatter.format_signal(signal)
                        await query.message.reply_text(msg)
                else:
                    await query.message.reply_text("⚠️ لم يتم العثور على إشارة سوينغ تتوافق مع شروط الفلترة وAI حالياً.\nسيتم الإرسال تلقائياً فور توفرها.")
            except Exception as e:
                logger.error(f"Callback Swing error: {e}")
                await query.message.reply_text("❌ حدث خطأ أثناء تحليل السوينغ.")


