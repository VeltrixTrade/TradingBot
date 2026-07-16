"""
Mustafa Bot - Telegram Bot Commands
أوامر البوت التفاعلية مع دعم تعدد الرموز (Multi-Symbol)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from bot.formatters import MessageFormatter
from config import Config

logger = logging.getLogger('mustafa_bot.bot.commands')


class BotCommands:
    """Handler class for all bot commands with dynamic symbol switching."""

    def __init__(self, signal_engine=None):
        self.signal_engine = signal_engine
        self.formatter = MessageFormatter()
        self.user_states = {}
        self.user_symbols = {}            # maps user_id -> symbol_key
        self.user_pending_actions = {}    # maps user_id -> (action_name, args, kwargs)

    async def check_user_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, *args, **kwargs) -> bool:
        """Verify if user has selected a symbol. If not, prompt with keyboard."""
        user_id = update.effective_user.id
        if user_id in self.user_symbols:
            return True

        # Save pending action
        self.user_pending_actions[user_id] = (action, args, kwargs)
        
        # Display symbol keyboard
        keyboard = [
            [
                InlineKeyboardButton("🟡 XAU/USD", callback_data="select_sym:XAU/USD"),
                InlineKeyboardButton("🔵 EUR/USD", callback_data="select_sym:EUR/USD")
            ],
            [
                InlineKeyboardButton("🟢 GBP/USD", callback_data="select_sym:GBP/USD"),
                InlineKeyboardButton("🟣 USD/JPY", callback_data="select_sym:USD/JPY")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_text = (
            "🌐 *يرجى اختيار رمز التداول المطلوب أولاً للبدء بالتحليل:*\n\n"
            "• 🟡 XAU/USD (الذهب)\n"
            "• 🔵 EUR/USD (اليورو/دولار)\n"
            "• 🟢 GBP/USD (الباوند/دولار)\n"
            "• 🟣 USD/JPY (الدولار/ين)"
        )
        if update.callback_query:
            await update.callback_query.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user_id = update.effective_user.id
        self.user_states[user_id] = 'normal'
        self.user_symbols.pop(user_id, None)  # Reset symbol selection

        # Remove persistent keyboard
        clear_msg = await update.message.reply_text("🔄 جاري تهيئة الواجهة...", reply_markup=ReplyKeyboardRemove())
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=clear_msg.message_id)
        except Exception:
            pass

        welcome = self.formatter.format_welcome()
        keyboard = [
            [
                InlineKeyboardButton("🔔 طلب إشارة فورية", callback_data="btn_signal"),
                InlineKeyboardButton("📊 تحليل السوق", callback_data="btn_analysis")
            ],
            [
                InlineKeyboardButton("🔮 توقع الأسعار", callback_data="btn_predict"),
                InlineKeyboardButton("🔄 تغيير الرمز", callback_data="btn_change_symbol")
            ],
            [
                InlineKeyboardButton("⚙️ الحالة والإحصائيات", callback_data="btn_status"),
                InlineKeyboardButton("💬 التحدث مع AI", callback_data="btn_chat")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome, reply_markup=reply_markup)
        logger.info(f'User {user_id} started the bot')

    async def symbol_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /symbol or Change Symbol command."""
        user_id = update.effective_user.id
        self.user_symbols.pop(user_id, None)
        self.user_pending_actions.pop(user_id, None)
        await self.check_user_symbol(update, context, 'menu')

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /signal command."""
        if not await self.check_user_symbol(update, context, 'signal'):
            return

        user_id = update.effective_user.id
        symbol_key = self.user_symbols[user_id]
        
        await update.message.reply_text(f'🔄 جاري تحليل {symbol_key}... يرجى الانتظار ⏳')
        try:
            if self.signal_engine is None:
                await update.message.reply_text('❌ محرك التحليل غير متوفر')
                return

            signals = await self.signal_engine.run_analysis('SCALP', is_manual=True, symbol_key=symbol_key)
            if not signals:
                signals = await self.signal_engine.run_analysis('SWING', is_manual=True, symbol_key=symbol_key)

            if signals:
                for signal in signals:
                    msg = self.formatter.format_signal(signal)
                    await update.message.reply_text(msg)
            else:
                await update.message.reply_text(
                    '⚠️ **No Trade Yet – Continue Monitoring**\n\n'
                    f'لم يتم العثور على إعداد صفقة لـ {symbol_key} يتطابق مع شروط الدقة المؤسساتية الصارمة (90/100) حالياً.\n'
                    'سيقوم النظام بالإرسال تلقائياً فور توفر الفرصة المناسبة في القناة 🔔',
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f'Signal command error: {e}', exc_info=True)
            await update.message.reply_text(f'❌ حدث خطأ أثناء التحليل: {str(e)[:100]}')

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /analysis command."""
        if not await self.check_user_symbol(update, context, 'analysis'):
            return

        user_id = update.effective_user.id
        symbol_key = self.user_symbols[user_id]

        await update.message.reply_text(f'📊 جاري تحليل سوق {symbol_key}... ⏳')
        try:
            if self.signal_engine is None:
                await update.message.reply_text('❌ محرك التحليل غير متوفر')
                return

            analysis_msg = await self.signal_engine.get_market_analysis(symbol_key=symbol_key)
            await update.message.reply_text(analysis_msg)
        except Exception as e:
            logger.error(f'Analysis command error: {e}', exc_info=True)
            await update.message.reply_text(f'❌ خطأ في التحليل: {str(e)[:100]}')

    async def predict_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /predict command."""
        if not await self.check_user_symbol(update, context, 'predict'):
            return

        user_id = update.effective_user.id
        symbol_key = self.user_symbols[user_id]

        await update.message.reply_text(f'🔮 جاري حساب توقعات {symbol_key}... ⏳')
        try:
            if self.signal_engine is None:
                await update.message.reply_text('❌ محرك التحليل غير متوفر')
                return

            prediction_msg = await self.signal_engine.get_prediction(symbol_key=symbol_key)
            await update.message.reply_text(prediction_msg)
        except Exception as e:
            logger.error(f'Predict command error: {e}', exc_info=True)
            await update.message.reply_text(f'❌ خطأ في التوقع: {str(e)[:100]}')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        try:
            if self.signal_engine:
                active = len(self.signal_engine.active_signals)
                total = self.signal_engine.total_signals
                wins = self.signal_engine.wins
                losses = self.signal_engine.losses
                total_trades = wins + losses
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                from datetime import datetime, timedelta
                last_update = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M:%S %p بتوقيت مكة المكرمة')
            else:
                active, total, win_rate, last_update = 0, 0, 0, 'N/A'

            msg = self.formatter.format_status(active, total, win_rate, last_update)
            await update.message.reply_text(msg)
        except Exception as e:
            logger.error(f'Status command error: {e}')
            await update.message.reply_text('❌ خطأ في جلب الحالة')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = """📖 المساعدة | Mustafa Bot
━━━━━━━━━━━━━━━━━━━━
📋 الأوامر المتاحة من لوحة الأزرار:

• 🔔 طلب إشارة فورية - اختيار إشارة سكالب أو سوينغ للرمز المختار
• 📊 تحليل السوق - تحليل فني مفصل لهيكل السوق والـ Order Blocks
• 🔮 توقع الأسعار - التوقعات السعرية ومناطق الارتداد
• 🔄 تغيير الرمز - تغيير الزوج/السلعة الحالية (/symbol)
• ⚙️ الحالة والإحصائيات - إحصائيات البوت ونسبة النجاح
• 💬 التحدث مع AI - محادثة تفاعلية مع مستشار التداول الخاص بك

📝 ملاحظات:
• يتم إرسال الإشارات تلقائياً لكافة الرموز المدعومة في القناة
• للتراجع أو الخروج من أي وضع، أرسل /cancel

⚠️ تحذير: التداول ينطوي على مخاطر عالية
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot v2.0"""

        keyboard = [
            [
                InlineKeyboardButton("🔔 طلب إشارة فورية", callback_data="btn_signal"),
                InlineKeyboardButton("📊 تحليل السوق", callback_data="btn_analysis")
            ],
            [
                InlineKeyboardButton("🔮 توقع الأسعار", callback_data="btn_predict"),
                InlineKeyboardButton("🔄 تغيير الرمز", callback_data="btn_change_symbol")
            ],
            [
                InlineKeyboardButton("⚙️ الحالة والإحصائيات", callback_data="btn_status"),
                InlineKeyboardButton("💬 التحدث مع AI", callback_data="btn_chat")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(help_text, reply_markup=reply_markup)

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command - exit chat mode."""
        user_id = update.effective_user.id
        self.user_states[user_id] = 'normal'
        await update.message.reply_text('🔙 تم الخروج من وضع التحدث مع الذكاء الاصطناعي والعودة للوضع الطبيعي.')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages to route button clicks and AI chat."""
        text = update.message.text
        user_id = update.effective_user.id
        current_state = self.user_states.get(user_id, 'normal')

        # Main menu button routings
        if text in ['🔔 طلب إشارة فورية', '📊 تحليل السوق', '🔮 توقع الأسعار', '🔄 تغيير الرمز', '⚙️ الحالة والإحصائيات', '💬 التحدث مع AI', 'تغيير الرمز', 'Change Symbol']:
            self.user_states[user_id] = 'normal'
            current_state = 'normal'

        if current_state == 'chat':
            await update.message.reply_text('🤔 جاري تفكير المستشار الذكي... ⏳')
            try:
                ai_response = await self.signal_engine.ai_manager.get_chat_response(text)
                await update.message.reply_text(ai_response)
            except Exception as e:
                logger.error(f'AI Chat error: {e}')
                await update.message.reply_text('❌ حدث خطأ أثناء معالجة رسالتك بالذكاء الاصطناعي.')
            return

        if text in ['تغيير الرمز', 'Change Symbol', '🔄 تغيير الرمز']:
            await self.symbol_command(update, context)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button clicks for signals and main menu."""
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = query.from_user.id

        # 1. Symbol Selection Callback Handling
        if data.startswith("select_sym:"):
            symbol_key = data.split(":")[1]
            self.user_symbols[user_id] = symbol_key
            await query.message.reply_text(f"✅ تم اختيار رمز التداول: *{symbol_key}* بنجاح.", parse_mode="Markdown")
            
            # Run pending action if exists
            pending = self.user_pending_actions.pop(user_id, None)
            if pending:
                action, args, kwargs = pending
                # Reconstruct Update object for commands
                mock_update = update
                if action == 'signal':
                    await self.signal_command(mock_update, context)
                elif action == 'analysis':
                    await self.analysis_command(mock_update, context)
                elif action == 'predict':
                    await self.predict_command(mock_update, context)
                elif action == 'get_scalp':
                    await self._execute_callback_scalp(query, symbol_key)
                elif action == 'get_swing':
                    await self._execute_callback_swing(query, symbol_key)
            return

        # 2. Main buttons routing
        if data == "btn_signal":
            if not await self.check_user_symbol(update, context, 'btn_signal'):
                return
            keyboard = [
                [
                    InlineKeyboardButton("⚡ إشارة سكالب (Scalp)", callback_data="get_scalp"),
                    InlineKeyboardButton("🌊 إشارة سوينغ (Swing)", callback_data="get_swing")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("📥 اختر نوع إشارة التداول المطلوبة:", reply_markup=reply_markup)

        elif data == "btn_analysis":
            if not await self.check_user_symbol(update, context, 'analysis'):
                return
            await self.analysis_command(update, context)

        elif data == "btn_predict":
            if not await self.check_user_symbol(update, context, 'predict'):
                return
            await self.predict_command(update, context)

        elif data == "btn_change_symbol":
            await self.symbol_command(update, context)

        elif data == "btn_status":
            await self.status_command(update, context)

        elif data == "btn_chat":
            self.user_states[user_id] = 'chat'
            chat_welcome = (
                "💬 لقد دخلت الآن وضع التحدث مع الذكاء الاصطناعي 🧠.\n\n"
                "اكتب أي سؤال بخصوص التداول، التحليل الفني، إدارة المخاطر، أو سلوك السوق، وسأجيبك فوراً!\n\n"
                "*(للخروج والعودة للوحة الأزرار، أرسل /cancel)*"
            )
            await query.message.reply_text(chat_welcome, parse_mode="Markdown")

        elif data == "get_scalp":
            if not await self.check_user_symbol(update, context, 'get_scalp'):
                return
            symbol_key = self.user_symbols[user_id]
            await self._execute_callback_scalp(query, symbol_key)

        elif data == "get_swing":
            if not await self.check_user_symbol(update, context, 'get_swing'):
                return
            symbol_key = self.user_symbols[user_id]
            await self._execute_callback_swing(query, symbol_key)

    async def _execute_callback_scalp(self, query, symbol_key: str) -> None:
        """Execute scalp analysis callback."""
        await query.message.reply_text(f"🔄 جاري تحليل {symbol_key} لإشارات السكالب (Scalp) عبر SMC + AI... ⏳")
        try:
            signals = await self.signal_engine.run_analysis('SCALP', is_manual=True, symbol_key=symbol_key)
            if signals:
                for signal in signals:
                    msg = self.formatter.format_signal(signal)
                    await query.message.reply_text(msg)
            else:
                await query.message.reply_text(
                    '⚠️ **No Trade Yet – Continue Monitoring**\n\n'
                    f'لم يتم العثور على إعداد صفقة سكالب لـ {symbol_key} يتوافق مع معايير الدقة المؤسساتية (90/100) حالياً.\n'
                    'سيتم الإرسال تلقائياً فور توفرها.',
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Callback Scalp error: {e}")
            await query.message.reply_text("❌ حدث خطأ أثناء تحليل السكالب.")

    async def _execute_callback_swing(self, query, symbol_key: str) -> None:
        """Execute swing analysis callback."""
        await query.message.reply_text(f"🔄 جاري تحليل {symbol_key} لإشارات السوينغ (Swing) عبر SMC + AI... ⏳")
        try:
            signals = await self.signal_engine.run_analysis('SWING', is_manual=True, symbol_key=symbol_key)
            if signals:
                for signal in signals:
                    msg = self.formatter.format_signal(signal)
                    await query.message.reply_text(msg)
            else:
                await query.message.reply_text(
                    '⚠️ **No Trade Yet – Continue Monitoring**\n\n'
                    f'لم يتم العثور على إعداد صفقة سوينغ لـ {symbol_key} يتوافق مع معايير الدقة المؤسساتية (90/100) حالياً.\n'
                    'سيتم الإرسال تلقائياً فور توفرها.',
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Callback Swing error: {e}")
            await query.message.reply_text("❌ حدث خطأ أثناء تحليل السوينغ.")
