"""
Mustafa Bot - Telegram Bot Commands
أوامر البوت التفاعلية الموحدة (Single-Message App Interface)
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.formatters import MessageFormatter
from bot.message_manager import MessageManager
from config import Config

logger = logging.getLogger('mustafa_bot.bot.commands')


class BotCommands:
    """Handler class for all bot commands with a persistent single-message interface."""

    def __init__(self, signal_engine=None):
        self.signal_engine = signal_engine
        self.formatter = MessageFormatter()
        self.msg_manager = MessageManager()
        self.user_states = {}             # maps user_id -> state string
        self.user_symbols = {}            # maps user_id -> symbol_key
        self.user_pending_actions = {}    # maps user_id -> (action_name, args, kwargs)

    async def get_main_menu(self, chat_id: int, bot) -> None:
        """Render the app-like persistent main menu screen."""
        welcome = self.formatter.format_welcome()
        
        # Display selected symbol in menu if exists
        symbol_text = self.user_symbols.get(chat_id, "لم يتم التحديد 🌐")
        welcome = f"🟢 *الرمز النشط الحالي*: `{symbol_text}`\n\n{welcome}"

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
        await self.msg_manager.send_or_edit(bot, chat_id, welcome, reply_markup)

    async def check_user_symbol(self, chat_id: int, bot, action: str, *args, **kwargs) -> bool:
        """Verify if user has selected a symbol. If not, prompt with inline selector."""
        if chat_id in self.user_symbols:
            return True

        # Save pending action to execute after selection
        self.user_pending_actions[chat_id] = (action, args, kwargs)
        
        keyboard = [
            [
                InlineKeyboardButton("🟡 XAU/USD", callback_data="select_sym:XAU/USD"),
                InlineKeyboardButton("🔵 EUR/USD", callback_data="select_sym:EUR/USD")
            ],
            [
                InlineKeyboardButton("🟢 GBP/USD", callback_data="select_sym:GBP/USD"),
                InlineKeyboardButton("🟣 USD/JPY", callback_data="select_sym:USD/JPY")
            ],
            [
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")
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
        await self.msg_manager.send_or_edit(bot, chat_id, msg_text, reply_markup)
        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Keep chat clean: delete incoming user message
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)

        # Reset session
        self.user_states[user_id] = 'MAIN_MENU'
        self.user_symbols.pop(chat_id, None)
        self.user_pending_actions.pop(chat_id, None)

        await self.get_main_menu(chat_id, context.bot)
        logger.info(f'User {user_id} started the bot interface')

    async def symbol_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /symbol command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        
        self.user_symbols.pop(chat_id, None)
        await self.check_user_symbol(chat_id, context.bot, 'menu')

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /signal command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        
        if not await self.check_user_symbol(chat_id, context.bot, 'signal'):
            return

        symbol_key = self.user_symbols[chat_id]
        await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /analysis command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        
        if not await self.check_user_symbol(chat_id, context.bot, 'analysis'):
            return

        symbol_key = self.user_symbols[chat_id]
        await self._run_interactive_market_analysis(chat_id, context.bot, symbol_key)

    async def predict_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /predict command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        
        if not await self.check_user_symbol(chat_id, context.bot, 'predict'):
            return

        symbol_key = self.user_symbols[chat_id]
        await self._run_interactive_prediction(chat_id, context.bot, symbol_key)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        await self._show_interactive_status(chat_id, context.bot)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        await self._show_interactive_help(chat_id, context.bot)

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        
        self.user_states[user_id] = 'MAIN_MENU'
        await self.get_main_menu(chat_id, context.bot)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle plain text messages to route AI chat or delete inputs immediately to keep chat clean."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        text = update.message.text
        
        # Delete user incoming message to keep the chat clean
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)

        current_state = self.user_states.get(user_id, 'MAIN_MENU')
        if current_state == 'chat':
            # Edit persistent message to show loading state
            await self.msg_manager.send_or_edit(
                context.bot,
                chat_id,
                "🤔 *جاري تفكير المستشار الذكي...* ⏳\n\nيرجى الانتظار لحين صياغة الرد المؤسساتي."
            )
            try:
                ai_response = await self.signal_engine.ai_manager.get_chat_response(text)
                formatted_response = (
                    f"💬 *رد مستشار التداول الذكي (AI Adviser)*:\n\n"
                    f"{ai_response}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💬 يمكنك كتابة أي سؤال آخر بخصوص التداول أو أسواق المال مباشرة."
                )
                keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await self.msg_manager.send_or_edit(context.bot, chat_id, formatted_response, reply_markup)
            except Exception as e:
                logger.error(f'AI Chat error: {e}')
                keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
                await self.msg_manager.send_or_edit(
                    context.bot,
                    chat_id,
                    "❌ *حدث خطأ أثناء معالجة رسالتك بالذكاء الاصطناعي.*",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all button callback queries."""
        query = update.callback_query
        await query.answer()
        data = query.data
        chat_id = query.message.chat_id
        user_id = query.from_user.id

        # 1. Symbol Selection Callback
        if data.startswith("select_sym:"):
            symbol_key = data.split(":")[1]
            self.user_symbols[chat_id] = symbol_key
            
            # Execute pending action if exists
            pending = self.user_pending_actions.pop(chat_id, None)
            if pending:
                action, args, kwargs = pending
                if action == 'signal':
                    await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)
                elif action == 'analysis':
                    await self._run_interactive_market_analysis(chat_id, context.bot, symbol_key)
                elif action == 'predict':
                    await self._run_interactive_prediction(chat_id, context.bot, symbol_key)
                elif action == 'get_scalp':
                    await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)
                elif action == 'get_swing':
                    await self._run_interactive_analysis(chat_id, context.bot, 'SWING', symbol_key)
            else:
                await self.get_main_menu(chat_id, context.bot)
            return

        # 2. Main buttons routing
        if data == "btn_home":
            self.user_states[user_id] = 'MAIN_MENU'
            await self.get_main_menu(chat_id, context.bot)

        elif data == "btn_signal":
            if not await self.check_user_symbol(chat_id, context.bot, 'btn_signal'):
                return
            symbol_key = self.user_symbols[chat_id]
            keyboard = [
                [
                    InlineKeyboardButton("⚡ إشارة سكالب (Scalp)", callback_data="get_scalp"),
                    InlineKeyboardButton("🌊 إشارة سوينغ (Swing)", callback_data="get_swing")
                ],
                [
                    InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.msg_manager.send_or_edit(
                context.bot,
                chat_id,
                f"📥 *الرمز الحالي*: `{symbol_key}`\n\nاختر نوع إشارة التداول المطلوبة:",
                reply_markup
            )

        elif data == "btn_analysis":
            if not await self.check_user_symbol(chat_id, context.bot, 'analysis'):
                return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_market_analysis(chat_id, context.bot, symbol_key)

        elif data == "btn_predict":
            if not await self.check_user_symbol(chat_id, context.bot, 'predict'):
                return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_prediction(chat_id, context.bot, symbol_key)

        elif data == "btn_change_symbol":
            self.user_symbols.pop(chat_id, None)
            await self.check_user_symbol(chat_id, context.bot, 'menu')

        elif data == "btn_status":
            await self._show_interactive_status(chat_id, context.bot)

        elif data == "btn_chat":
            self.user_states[user_id] = 'chat'
            chat_welcome = (
                "💬 لقد دخلت الآن وضع التحدث مع الذكاء الاصطناعي 🧠.\n\n"
                "اكتب أي سؤال بخصوص التداول، التحليل الفني، إدارة المخاطر، أو سلوك السوق، وسأجيبك فوراً!\n\n"
                "*(للخروج والعودة للوحة الأزرار الرئيسية، اضغط على زر القائمة بالأسفل)*"
            )
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(context.bot, chat_id, chat_welcome, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "get_scalp":
            if not await self.check_user_symbol(chat_id, context.bot, 'get_scalp'):
                return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)

        elif data == "get_swing":
            if not await self.check_user_symbol(chat_id, context.bot, 'get_swing'):
                return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_analysis(chat_id, context.bot, 'SWING', symbol_key)

    # ─────────────────────────────────────────────
    # Animated Loading and Action Executives
    # ─────────────────────────────────────────────

    async def _run_interactive_analysis(self, chat_id: int, bot, signal_type: str, symbol_key: str) -> None:
        """Run step-by-step loading animation before displaying signal output."""
        loading_steps = [
            "🔄 [1/6] Collecting live market data...",
            "🔄 [2/6] Detecting Market Structure (BOS/CHoCH)...",
            "🔄 [3/6] Mapping Liquidity Pools & Sweeps...",
            "🔄 [4/6] Locating Order Blocks & Breakers...",
            "🔄 [5/6] Validating Smart Money & IFVG...",
            "🔄 [6/6] Calculating Trade Quality Score..."
        ]

        for step in loading_steps:
            await self.msg_manager.send_or_edit(bot, chat_id, f"⚡ *{symbol_key} ({signal_type})*:\n\n{step}")
            await asyncio.sleep(0.4)

        try:
            signals = await self.signal_engine.run_analysis(signal_type, is_manual=True, symbol_key=symbol_key)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if signals:
                for signal in signals:
                    msg = self.formatter.format_signal(signal)
                    await self.msg_manager.send_or_edit(bot, chat_id, msg, reply_markup)
            else:
                await self.msg_manager.send_or_edit(
                    bot,
                    chat_id,
                    f"⚠️ **No Trade Yet – Continue Monitoring**\n\n"
                    f"لم يتم العثور على إعداد صفقة لـ {symbol_key} يتوافق مع معايير الدقة المؤسساتية (90/100) حالياً.\n"
                    f"سيقوم النظام بالإرسال تلقائياً فور توفر الفرصة المناسبة.",
                    reply_markup
                )
        except Exception as e:
            logger.error(f"Interactive analysis error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء إجراء التحليل.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _run_interactive_market_analysis(self, chat_id: int, bot, symbol_key: str) -> None:
        """Run loading animation and show market analysis dashboard."""
        await self.msg_manager.send_or_edit(bot, chat_id, f"📊 *{symbol_key}*:\n\n🔄 Scanning market structure and indicators...")
        await asyncio.sleep(0.5)

        try:
            analysis_msg = await self.signal_engine.get_market_analysis(symbol_key=symbol_key)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, analysis_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Interactive market analysis error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء جلب تحليل السوق.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _run_interactive_prediction(self, chat_id: int, bot, symbol_key: str) -> None:
        """Run prediction logic."""
        await self.msg_manager.send_or_edit(bot, chat_id, f"🔮 *{symbol_key}*:\n\n🔄 Processing predictions via institutional models...")
        await asyncio.sleep(0.5)

        try:
            prediction_msg = await self.signal_engine.get_prediction(symbol_key=symbol_key)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, prediction_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Interactive prediction error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء حساب التوقعات.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_status(self, chat_id: int, bot) -> None:
        """Show status page."""
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
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Show status error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *خطأ في جلب حالة النظام.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_help(self, chat_id: int, bot) -> None:
        """Show help page."""
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
        keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
        await self.msg_manager.send_or_edit(bot, chat_id, help_text, reply_markup=InlineKeyboardMarkup(keyboard))
