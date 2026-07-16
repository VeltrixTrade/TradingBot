"""
Mustafa Bot - Telegram Bot Commands
أوامر البوت التفاعلية الموحدة بأسلوب التطبيق التفاعلي الموحد (Institutional Application Dashboard)
"""

import logging
import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.formatters import MessageFormatter
from bot.message_manager import MessageManager
from database.db_manager import DatabaseManager
from analytics.performance import PerformanceAnalyticsEngine
from backtest.engine import HistoricalBacktestEngine
from utils.diagnostics import DiagnosticsManager
from config import Config

logger = logging.getLogger('mustafa_bot.bot.commands')


class BotCommands:
    """Handler class for all bot commands with a persistent single-message interface."""

    def __init__(self, signal_engine=None):
        self.signal_engine = signal_engine
        self.formatter = MessageFormatter()
        self.msg_manager = MessageManager()
        self.db = DatabaseManager()
        self.analytics = PerformanceAnalyticsEngine(self.db)
        self.backtester = HistoricalBacktestEngine()
        self.diagnostics = DiagnosticsManager()

        self.user_states = {}             # maps chat_id -> state string
        self.user_symbols = {}            # maps chat_id -> symbol_key
        self.user_profiles = {}           # maps chat_id -> profile_key ('CONSERVATIVE' or 'AGGRESSIVE')
        self.user_pending_actions = {}    # maps chat_id -> (action_name, args, kwargs)

    def _get_user_profile(self, chat_id: int) -> str:
        return self.user_profiles.get(chat_id, Config.DEFAULT_PROFILE)

    async def get_main_menu(self, chat_id: int, bot) -> None:
        """Render the persistent dashboard main menu screen."""
        symbol_text = self.user_symbols.get(chat_id, "لم يتم التحديد 🌐")
        profile_key = self._get_user_profile(chat_id)
        profile_name = Config.TRADING_PROFILES[profile_key]['name']
        active_trades_count = len(self.db.get_active_trades())

        # Determine current active session
        from utils.scheduler import AnalysisScheduler
        current_hour_utc = datetime.now(timezone.utc).hour
        active_sessions = []
        if 8 <= current_hour_utc < 16: active_sessions.append("LONDON 🇬🇧")
        if 13 <= current_hour_utc < 21: active_sessions.append("NEW YORK 🇺🇸")
        if 0 <= current_hour_utc < 8: active_sessions.append("ASIAN 🇯🇵")
        session_text = " + ".join(active_sessions) if active_sessions else "TRANSITION PERIOD 💤"

        dashboard_header = self.formatter.format_dashboard_status(
            symbol=symbol_text,
            profile_name=profile_name,
            active_trades_count=active_trades_count,
            data_feed_status=self.diagnostics.data_feed_status,
            last_analysis_time=self.diagnostics.last_analysis_time or "جاهز",
            active_session=session_text
        )

        welcome = self.formatter.format_welcome()
        full_text = f"{dashboard_header}\n\n{welcome}"

        keyboard = [
            [
                InlineKeyboardButton("🔔 طلب إشارة فورية", callback_data="btn_signal"),
                InlineKeyboardButton("📊 تحليل السوق", callback_data="btn_analysis")
            ],
            [
                InlineKeyboardButton("🔮 توقع الأسعار", callback_data="btn_predict"),
                InlineKeyboardButton("📈 إحصائيات الأداء", callback_data="btn_performance")
            ],
            [
                InlineKeyboardButton("🔄 تغيير الرمز", callback_data="btn_change_symbol"),
                InlineKeyboardButton("⚙️ نمط التداول والمخاطرة", callback_data="btn_settings")
            ],
            [
                InlineKeyboardButton("📋 سجل الصفقات", callback_data="btn_history"),
                InlineKeyboardButton("🧪 اختبار تاريخي (Backtest)", callback_data="btn_backtest")
            ],
            [
                InlineKeyboardButton("🛠️ تشخيص الخادم", callback_data="btn_diagnostics"),
                InlineKeyboardButton("💬 التحدث مع AI", callback_data="btn_chat")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.msg_manager.send_or_edit(bot, chat_id, full_text, reply_markup)

    async def check_user_symbol(self, chat_id: int, bot, action: str, *args, **kwargs) -> bool:
        """Verify if user has selected a symbol. If not, prompt with inline selector."""
        if chat_id in self.user_symbols:
            return True

        self.user_pending_actions[chat_id] = (action, args, kwargs)
        
        # Load all symbols dynamically from config
        symbols_dict = Config.SUPPORTED_SYMBOLS
        keyboard = []
        row = []
        for sym_key, sym_data in symbols_dict.items():
            btn_display = sym_data.get('display', sym_key)
            row.append(InlineKeyboardButton(btn_display, callback_data=f"select_sym:{sym_key}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_text = (
            "🌐 *يرجى اختيار رمز التداول المطلوب أولاً للبدء بالتحليل المؤسساتي:*\n\n"
            "انقر على الزوج أو السلعة أو المؤشر من اللوائح التفاعلية أدناه:"
        )
        await self.msg_manager.send_or_edit(bot, chat_id, msg_text, reply_markup)
        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)

        self.user_states[user_id] = 'MAIN_MENU'
        self.user_symbols.pop(chat_id, None)
        self.user_pending_actions.pop(chat_id, None)

        await self.get_main_menu(chat_id, context.bot)
        self.diagnostics.log_event("BotCommands", "INFO", f"User {user_id} started session")

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
        """Handle incoming text messages to route AI chat or delete inputs immediately."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        text = update.message.text
        
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)

        current_state = self.user_states.get(user_id, 'MAIN_MENU')
        if current_state == 'chat':
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

        # 2. Settings Profile Toggle
        elif data.startswith("set_profile:"):
            profile_key = data.split(":")[1]
            self.user_profiles[chat_id] = profile_key
            await self._show_interactive_settings(chat_id, context.bot)
            return

        # 3. Main buttons routing
        if data in ["btn_home", "btn_dashboard"]:
            self.user_states[user_id] = 'MAIN_MENU'
            await self.get_main_menu(chat_id, context.bot)

        elif data == "btn_signal":
            if not await self.check_user_symbol(chat_id, context.bot, 'btn_signal'):
                return
            symbol_key = self.user_symbols[chat_id]
            profile_key = self._get_user_profile(chat_id)
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
                f"📥 *الرمز الحالي*: `{symbol_key}` | النمط: `{profile_key}`\n\nاختر نوع إشارة التداول المطلوبة:",
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

        elif data == "btn_performance":
            symbol_key = self.user_symbols.get(chat_id)
            await self._show_interactive_performance(chat_id, context.bot, symbol_key)

        elif data == "btn_history":
            await self._show_interactive_history(chat_id, context.bot)

        elif data == "btn_backtest":
            if not await self.check_user_symbol(chat_id, context.bot, 'backtest'):
                return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_backtest(chat_id, context.bot, symbol_key)

        elif data == "btn_settings":
            await self._show_interactive_settings(chat_id, context.bot)

        elif data == "btn_diagnostics":
            await self._show_interactive_diagnostics(chat_id, context.bot)

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
    # Interactive Screen Executives
    # ─────────────────────────────────────────────

    async def _run_interactive_analysis(self, chat_id: int, bot, signal_type: str, symbol_key: str) -> None:
        """Run step-by-step loading animation before displaying signal output."""
        profile_key = self._get_user_profile(chat_id)
        loading_steps = [
            f"🔄 [1/6] Scanning live feeds for {symbol_key}...",
            "🔄 [2/6] Detecting Market Structure (BOS/CHoCH)...",
            "🔄 [3/6] Mapping Liquidity Pools & Stop Sweeps...",
            "🔄 [4/6] Locating Order Blocks & Breakers...",
            "🔄 [5/6] Validating Smart Money & IFVG...",
            f"🔄 [6/6] Scoring setup against profile ({profile_key})..."
        ]

        for step in loading_steps:
            await self.msg_manager.send_or_edit(bot, chat_id, f"⚡ *{symbol_key} ({signal_type})*:\n\n{step}")
            await asyncio.sleep(0.3)

        self.diagnostics.update_last_analysis_time()

        try:
            signals = await self.signal_engine.run_analysis(signal_type, is_manual=True, symbol_key=symbol_key, profile=profile_key)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if signals:
                for signal in signals:
                    msg = self.formatter.format_signal(signal)
                    
                    # Store signal trade into SQLite DB
                    self.db.insert_trade({
                        'id': signal.id,
                        'symbol': symbol_key,
                        'direction': signal.direction.value,
                        'timeframe': signal.timeframe,
                        'entry': signal.entry,
                        'stop_loss': signal.stop_loss,
                        'tp1': signal.take_profit_1,
                        'tp2': signal.take_profit_2,
                        'tp3': signal.take_profit_3,
                        'confidence_score': signal.confidence,
                        'risk_reward': signal.risk_reward,
                        'status': 'WAITING_ENTRY',
                        'analysis_report': msg
                    })

                    await self.msg_manager.send_or_edit(bot, chat_id, msg, reply_markup)
            else:
                profile_info = Config.TRADING_PROFILES[profile_key]
                await self.msg_manager.send_or_edit(
                    bot,
                    chat_id,
                    f"⚠️ **No Trade Yet – Continue Monitoring**\n\n"
                    f"لم يتم العثور على إعداد صفقة لـ *{symbol_key}* يتوافق مع معايير نمط (*{profile_info['name']}*) "
                    f"والتي تتطلب حد نقاط أدنى {profile_info['min_score']}/100 حالياً.\n"
                    f"سيقوم النظام بالإرسال تلقائياً فور توفر الفرصة المناسبة.",
                    reply_markup
                )
        except Exception as e:
            logger.error(f"Interactive analysis error: {e}", exc_info=True)
            self.diagnostics.log_event("Analysis", "ERROR", f"Analysis error for {symbol_key}: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء إجراء التحليل.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _run_interactive_market_analysis(self, chat_id: int, bot, symbol_key: str) -> None:
        """Run loading animation and show market analysis dashboard."""
        await self.msg_manager.send_or_edit(bot, chat_id, f"📊 *{symbol_key}*:\n\n🔄 Scanning multi-timeframe structure and indicators...")
        await asyncio.sleep(0.4)

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
        await self.msg_manager.send_or_edit(bot, chat_id, f"🔮 *{symbol_key}*:\n\n🔄 Processing predictions via institutional AI models...")
        await asyncio.sleep(0.4)

        try:
            prediction_msg = await self.signal_engine.get_prediction(symbol_key=symbol_key)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, prediction_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Interactive prediction error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء حساب التوقعات.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_performance(self, chat_id: int, bot, symbol: Optional[str] = None) -> None:
        """Show performance metrics page."""
        try:
            metrics = self.analytics.calculate_performance_summary(symbol=symbol)
            summary_text = metrics['formatted_summary']
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, summary_text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Performance display error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *خطأ في جلب تقرير الأداء.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_history(self, chat_id: int, bot) -> None:
        """Show trade history page."""
        try:
            trades = self.db.get_all_trades(limit=15)
            history_text = MessageFormatter.format_trade_history(trades)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, history_text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"History display error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *خطأ في جلب سجل الصفقات.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _run_interactive_backtest(self, chat_id: int, bot, symbol_key: str) -> None:
        """Run interactive historical backtest."""
        profile_key = self._get_user_profile(chat_id)
        await self.msg_manager.send_or_edit(bot, chat_id, f"🧪 *اختبار الاستراتيجية لـ {symbol_key}* ({profile_key})...\n\n🔄 Simulate candle slices & scoring validation...")
        await asyncio.sleep(0.5)

        try:
            bt_res = self.backtester.run_backtest(symbol_key=symbol_key, signal_type='SCALP', n_bars=500, profile=profile_key)
            report_text = bt_res.get('formatted_report', 'تعذر تنفيذ الاختبار')
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, report_text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Backtest execution error: {e}", exc_info=True)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء إجراء الاختبار التاريخي.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_settings(self, chat_id: int, bot) -> None:
        """Show user settings and profile toggle options."""
        current_profile = self._get_user_profile(chat_id)
        cons_cfg = Config.TRADING_PROFILES['CONSERVATIVE']
        agg_cfg = Config.TRADING_PROFILES['AGGRESSIVE']

        text = (
            f"⚙️ *إعدادات نمط التداول وشروط الفلترة*:\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"النمط المفعل حالياً: *{Config.TRADING_PROFILES[current_profile]['name']}*\n\n"
            f"• 🛡️ *النمط المحافظ (Conservative)*:\n"
            f"  - الحد الأدنى للتقييم: *{cons_cfg['min_score']}/100*\n"
            f"  - أدنى نسبة عائد للسكالب/السوينغ: *1:{cons_cfg['min_rr_scalp']} / 1:{cons_cfg['min_rr_swing']}*\n"
            f"  - يركز على الصفقات فائقة التأكيد والقليلة التكرار.\n\n"
            f"• ⚡ *النمط الهجومي (Aggressive)*:\n"
            f"  - الحد الأدنى للتقييم: *{agg_cfg['min_score']}/100*\n"
            f"  - أدنى نسبة عائد للسكالب/السوينغ: *1:{agg_cfg['min_rr_scalp']} / 1:{agg_cfg['min_rr_swing']}*\n"
            f"  - يوفر فرصاً أكثر مع الحفاظ على إدارة المخاطر.\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"اختر النمط المطلوب للبدء بالتطبيق الفوري:"
        )

        keyboard = [
            [
                InlineKeyboardButton(f"{'✅ ' if current_profile == 'CONSERVATIVE' else ''}🛡️ المحافظ (90+)", callback_data="set_profile:CONSERVATIVE"),
                InlineKeyboardButton(f"{'✅ ' if current_profile == 'AGGRESSIVE' else ''}⚡ الهجومي (75+)", callback_data="set_profile:AGGRESSIVE")
            ],
            [
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")
            ]
        ]
        await self.msg_manager.send_or_edit(bot, chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_diagnostics(self, chat_id: int, bot) -> None:
        """Show diagnostics logs page."""
        diag_report = self.diagnostics.get_system_health_report()
        keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
        await self.msg_manager.send_or_edit(bot, chat_id, diag_report, reply_markup=InlineKeyboardMarkup(keyboard))

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
• 📈 إحصائيات الأداء - تحليل كَمّي للشخصية والأرباح والـ Sharpe
• 🔄 تغيير الرمز - تغيير الزوج/السلعة الحالية (/symbol)
• ⚙️ نمط التداول - التنقل بين النمط المحافظ (90+) والهجومي (75+)
• 🧪 الاختبار التاريخي - فحص نتائج الاستراتيجية على البيانات التاريخية
• 🛠️ تشخيص الخادم - مراقبة حالة جلب البيانات وصحة السيرفر

⚠️ تحذير: التداول ينطوي على مخاطر عالية
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot v2.5"""
        keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
        await self.msg_manager.send_or_edit(bot, chat_id, help_text, reply_markup=InlineKeyboardMarkup(keyboard))
