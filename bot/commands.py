"""
Mustafa Bot - Telegram Bot Commands
أوامر البوت التفاعلية الموحدة بأسلوب التطبيق التفاعلي الموحد ومعالج إعداد حسابات MT5 الشامل
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
from utils.crypto_vault import CryptoVault
from data.mt5_wizard import MT5SetupWizard
from data.mt5_connection import MT5ConnectionManager
from config import Config

logger = logging.getLogger('mustafa_bot.bot.commands')


class BotCommands:
    """Handler class for all bot commands with persistent single-message UI and MT5 Setup Wizard."""

    def __init__(self, signal_engine=None):
        self.signal_engine = signal_engine
        self.formatter = MessageFormatter()
        self.msg_manager = MessageManager()
        self.db = DatabaseManager()
        self.analytics = PerformanceAnalyticsEngine(self.db)
        self.backtester = HistoricalBacktestEngine()
        self.diagnostics = DiagnosticsManager()
        self.mt5_wizard = MT5SetupWizard()
        self.mt5_mgr = MT5ConnectionManager()
        self.crypto_vault = CryptoVault()

        self.user_states = {}             # maps chat_id -> state string
        self.user_symbols = {}            # maps chat_id -> symbol_key
        self.user_profiles = {}           # maps chat_id -> profile_key
        self.user_pending_actions = {}    # maps chat_id -> (action_name, args, kwargs)

    def _get_user_profile(self, chat_id: int) -> str:
        return self.user_profiles.get(chat_id, Config.DEFAULT_PROFILE)

    async def get_main_menu(self, chat_id: int, bot) -> None:
        """Render the persistent dashboard main menu screen."""
        symbol_text = self.user_symbols.get(chat_id, "لم يتم التحديد 🌐")
        profile_key = self._get_user_profile(chat_id)
        profile_name = Config.TRADING_PROFILES[profile_key]['name']
        active_trades_count = len(self.db.get_active_trades())

        # Active Session
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
                InlineKeyboardButton("🎯 معايرة السعر", callback_data="btn_calibrate_price"),
                InlineKeyboardButton("⚙️ نمط التداول والمخاطرة", callback_data="btn_settings")
            ],
            [
                InlineKeyboardButton("🔄 تغيير الرمز", callback_data="btn_change_symbol"),
                InlineKeyboardButton("📋 سجل الصفقات", callback_data="btn_history")
            ],
            [
                InlineKeyboardButton("🧪 اختبار تاريخي (Backtest)", callback_data="btn_backtest"),
                InlineKeyboardButton("🛠️ تشخيص الخادم", callback_data="btn_diagnostics")
            ],
            [
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
        msg_text = "🌐 *يرجى اختيار رمز التداول المطلوب أولاً للبدء بالتحليل المؤسساتي:*"
        await self.msg_manager.send_or_edit(bot, chat_id, msg_text, reply_markup)
        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)

        self.user_states[user_id] = 'MAIN_MENU'
        self.mt5_wizard.reset_wizard(chat_id)
        self.user_symbols.pop(chat_id, None)
        self.user_pending_actions.pop(chat_id, None)

        await self.get_main_menu(chat_id, context.bot)

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
        if not await self.check_user_symbol(chat_id, context.bot, 'signal'): return
        symbol_key = self.user_symbols[chat_id]
        await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /analysis command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        if not await self.check_user_symbol(chat_id, context.bot, 'analysis'): return
        symbol_key = self.user_symbols[chat_id]
        await self._run_interactive_market_analysis(chat_id, context.bot, symbol_key)

    async def predict_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /predict command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        if not await self.check_user_symbol(chat_id, context.bot, 'predict'): return
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
        self.mt5_wizard.reset_wizard(chat_id)
        await self.get_main_menu(chat_id, context.bot)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle plain text messages to process wizard inputs, AI chat, or delete inputs immediately."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        text = update.message.text
        
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)

        # Check if user is in MT5 Setup Wizard flow
        wizard_step = self.mt5_wizard.get_current_step(chat_id)
        if wizard_step != 'IDLE':
            next_step, wizard_msg = self.mt5_wizard.record_input(chat_id, text)
            
            if next_step == 'CONFIRMATION':
                keyboard = [
                    [
                        InlineKeyboardButton("✅ اتصال بـ MT5", callback_data="btn_confirm_mt5_connect"),
                        InlineKeyboardButton("✏️ إعـادة الإعداد", callback_data="btn_start_mt5_wizard")
                    ],
                    [
                        InlineKeyboardButton("❌ إلغـاء", callback_data="btn_home")
                    ]
                ]
            else:
                keyboard = [[InlineKeyboardButton("❌ إلغاء المعالج", callback_data="btn_home")]]

            await self.msg_manager.send_or_edit(context.bot, chat_id, wizard_msg, reply_markup=InlineKeyboardMarkup(keyboard))
            return

        current_state = self.user_states.get(user_id, 'MAIN_MENU')
        if current_state == 'chat':
            await self.msg_manager.send_or_edit(context.bot, chat_id, "🤔 *جاري تفكير المستشار الذكي...* ⏳")
            try:
                ai_response = await self.signal_engine.ai_manager.get_chat_response(text)
                formatted = f"💬 *رد مستشار التداول الذكي (AI)*:\n\n{ai_response}\n\n━━━━━━━━━━━━━━━━━━━━\n💬 يمكنك كتابة أي سؤال آخر مباشرة."
                keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
                await self.msg_manager.send_or_edit(context.bot, chat_id, formatted, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception as e:
                logger.error(f'AI Chat error: {e}')
                keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
                await self.msg_manager.send_or_edit(context.bot, chat_id, "❌ *حدث خطأ أثناء الرد.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all button callback queries."""
        query = update.callback_query
        await query.answer()
        data = query.data
        chat_id = query.message.chat_id
        user_id = query.from_user.id

        # 1. Symbol Selection
        if data.startswith("select_sym:"):
            symbol_key = data.split(":")[1]
            self.user_symbols[chat_id] = symbol_key
            pending = self.user_pending_actions.pop(chat_id, None)
            if pending:
                action, args, kwargs = pending
                if action == 'signal': await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)
                elif action == 'analysis': await self._run_interactive_market_analysis(chat_id, context.bot, symbol_key)
                elif action == 'predict': await self._run_interactive_prediction(chat_id, context.bot, symbol_key)
                elif action == 'get_scalp': await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)
                elif action == 'get_swing': await self._run_interactive_analysis(chat_id, context.bot, 'SWING', symbol_key)
            else:
                await self.get_main_menu(chat_id, context.bot)
            return

        # 2. Profile Selection
        elif data.startswith("set_profile:"):
            profile_key = data.split(":")[1]
            self.user_profiles[chat_id] = profile_key
            await self._show_interactive_settings(chat_id, context.bot)
            return

        # 3. MT5 Wizard Callbacks & Calibration
        elif data == "btn_mt5_account" or data == "btn_mt5_settings":
            await self._show_interactive_mt5_dashboard(chat_id, context.bot)

        elif data == "btn_calibrate_price":
            await self._show_price_calibration_screen(chat_id, context.bot)

        elif data.startswith("adjust_offset:"):
            change_val = float(data.split(":")[1])
            sym_key = self.user_symbols.get(chat_id, 'XAU/USD')
            from data.price_calibrator import BrokerPriceCalibrator
            calibrator = BrokerPriceCalibrator()
            
            if change_val == 0.0:
                calibrator.reset_user_offset(chat_id, sym_key)
            else:
                current_off = calibrator.get_user_offset(chat_id, sym_key)
                calibrator.set_user_offset(chat_id, sym_key, current_off + change_val)
            
            await self._show_price_calibration_screen(chat_id, context.bot)

        elif data == "btn_start_mt5_wizard":
            self.mt5_wizard.start_wizard(chat_id)
            prompt = (
                "🔗 *معالج إعداد اتصال حساب MetaTrader 5*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🏦 *الخطوة [1/5]*: يرجى كتابة اسم الوسيط المالية (*Broker Name*) مثل:\n"
                "`IC Markets` أو `Exness` أو `XM`"
            )
            keyboard = [[InlineKeyboardButton("❌ إلغاء المعالج", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(context.bot, chat_id, prompt, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "btn_confirm_mt5_connect":
            await self._execute_mt5_connection(chat_id, context.bot)

        elif data == "btn_disconnect_mt5":
            self.db.delete_mt5_account(chat_id)
            self.mt5_wizard.reset_wizard(chat_id)
            await self.msg_manager.send_or_edit(
                context.bot,
                chat_id,
                "🗑️ *تم قطع الاتصال وحذف بيانات حساب MT5 المشفرة بنجاح.*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]])
            )

        # 4. Standard App Navigation
        elif data in ["btn_home", "btn_dashboard"]:
            self.user_states[user_id] = 'MAIN_MENU'
            self.mt5_wizard.reset_wizard(chat_id)
            await self.get_main_menu(chat_id, context.bot)

        elif data == "btn_signal":
            if not await self.check_user_symbol(chat_id, context.bot, 'btn_signal'): return
            symbol_key = self.user_symbols[chat_id]
            keyboard = [
                [InlineKeyboardButton("⚡ إشارة سكالب (Scalp)", callback_data="get_scalp"), InlineKeyboardButton("🌊 إشارة سوينغ (Swing)", callback_data="get_swing")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]
            ]
            await self.msg_manager.send_or_edit(context.bot, chat_id, f"📥 *الرمز الحالي*: `{symbol_key}`\n\nاختر نوع الإشارة المطلوبة:", InlineKeyboardMarkup(keyboard))

        elif data == "btn_analysis":
            if not await self.check_user_symbol(chat_id, context.bot, 'analysis'): return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_market_analysis(chat_id, context.bot, symbol_key)

        elif data == "btn_predict":
            if not await self.check_user_symbol(chat_id, context.bot, 'predict'): return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_prediction(chat_id, context.bot, symbol_key)

        elif data == "btn_performance":
            symbol_key = self.user_symbols.get(chat_id)
            await self._show_interactive_performance(chat_id, context.bot, symbol_key)

        elif data == "btn_history":
            await self._show_interactive_history(chat_id, context.bot)

        elif data == "btn_backtest":
            if not await self.check_user_symbol(chat_id, context.bot, 'backtest'): return
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
                "💬 لقد دخلت وضع التحدث مع الذكاء الاصطناعي 🧠.\n\n"
                "اكتب أي سؤال بخصوص التداول مباشرة وسأجيبك فوراً!"
            )
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(context.bot, chat_id, chat_welcome, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "get_scalp":
            if not await self.check_user_symbol(chat_id, context.bot, 'get_scalp'): return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)

        elif data == "get_swing":
            if not await self.check_user_symbol(chat_id, context.bot, 'get_swing'): return
            symbol_key = self.user_symbols[chat_id]
            await self._run_interactive_analysis(chat_id, context.bot, 'SWING', symbol_key)

    # ─────────────────────────────────────────────
    # MT5 Wizard Execution & Dashboard Screens
    # ─────────────────────────────────────────────

    async def _execute_mt5_connection(self, chat_id: int, bot) -> None:
        """Encrypt credentials, persist, and verify MT5 live account connection."""
        await self.msg_manager.send_or_edit(bot, chat_id, "🔐 *جاري تشفير بيانات الحساب واختبار الاتصال بمنصة MT5...* ⏳")
        await asyncio.sleep(0.5)

        data = self.mt5_wizard.user_wizard_data.get(chat_id, {})
        broker = data.get('broker_name', '')
        server = data.get('server', '')
        login = data.get('login', 0)
        password = data.get('password', '')

        # Encrypt password using Fernet Vault
        enc_pwd = self.crypto_vault.encrypt_secret(password)
        self.db.save_mt5_account(chat_id, broker, server, login, enc_pwd)

        # Test login connection via MT5 Connection Manager
        success = self.mt5_mgr.connect(chat_id=chat_id)
        self.mt5_wizard.reset_wizard(chat_id)

        if success:
            sym_count = len(self.mt5_mgr.broker_symbols)
            msg = (
                f"✅ *تم الاتصال بحساب MetaTrader 5 بنجاح!*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🏦 الوسيط: *{broker}*\n"
                f"🌐 الخادم: *{server}*\n"
                f"🔢 رقم الحساب: `{login}`\n"
                f"📡 حالة الاتصال: *نشط ومتصل (Live Data)*\n"
                f"📈 الرموز المكتشفة أوتوماتيكياً: *{sym_count} أصول*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"جميع تحليلات وإشارات البوت ستستخدم الآن بيانات حسابك المباشر."
            )
            keyboard = [
                [InlineKeyboardButton("⚙️ إعدادات MT5", callback_data="btn_mt5_settings")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]
            ]
        else:
            msg = (
                f"⚠️ *تعذر إكمال الاتصال بحساب MT5*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"يرجى التأكد من:\n"
                f"• تشغيل برنامج MetaTrader 5 على الجهاز.\n"
                f"• صحة رقم الحساب ({login}) وكلمة المرور وسيرفر الوسيط ({server}).\n"
                f"• تفعيل خيار 'Allow Algo Trading' في المنصة."
            )
            keyboard = [
                [InlineKeyboardButton("✏️ إعادة المحاولة المعالج", callback_data="btn_start_mt5_wizard")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]
            ]

        await self.msg_manager.send_or_edit(bot, chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_mt5_dashboard(self, chat_id: int, bot) -> None:
        """Render Dedicated Pure Native MT5 Connection & Account Management Dashboard."""
        acc_db = self.db.get_mt5_account(chat_id)
        
        # Verify active MT5 connection details
        self.mt5_mgr.connect(chat_id=chat_id)
        is_conn = self.mt5_mgr.is_initialized
        acc_info = self.mt5_mgr.active_account_info
        term_info = self.mt5_mgr.terminal_info

        sym_key = self.user_symbols.get(chat_id, 'XAU/USD')
        from data.price_fetcher import PriceFetcher
        from data.price_calibrator import BrokerPriceCalibrator
        calibrator = BrokerPriceCalibrator()

        current_p = PriceFetcher(sym_key).get_current_price(chat_id=chat_id)
        current_offset = calibrator.get_user_offset(chat_id, sym_key)

        status_str = "متصل ومزامن بنجاح 🟢 (Pure Native MT5 API)" if is_conn else "غير متصل 🛑 (في انتظار الاتصال)"
        ping_ms = round(term_info.get('ping_last', 0) / 1000.0, 1) if term_info else 0.0
        build_ver = term_info.get('build', 'Build 4400+') if term_info else 'N/A'

        login_val = acc_info.get('login') or (acc_db['login'] if acc_db else Config.MT5_LOGIN or 'N/A')
        server_val = acc_info.get('server') or (acc_db['server'] if acc_db else Config.MT5_SERVER or 'N/A')
        broker_val = acc_info.get('company') or (acc_db['broker_name'] if acc_db else 'MetaTrader 5 Broker')
        balance_val = f"${acc_info.get('balance', 0.0):,.2f}" if acc_info else 'N/A'
        equity_val = f"${acc_info.get('equity', 0.0):,.2f}" if acc_info else 'N/A'
        leverage_val = f"1:{acc_info.get('leverage', 500)}" if acc_info else '1:500'

        sym_count = len(self.mt5_mgr.broker_symbols) or 8

        text = (
            f"⚙️ *منصة وتفاصيل اتصال MetaTrader 5 المباشر (Pure MT5 API)*:\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 حالة الاتصال: *{status_str}*\n"
            f"⏱️ زمن الاستجابة (Ping Latency): *{ping_ms} ms*\n"
            f"🛠️ إصدار المنصة (Build): *{build_ver}*\n\n"
            f"🏦 اسم الوسيط (Broker): *{broker_val}*\n"
            f"🌐 خادم الحساب (Server): *{server_val}*\n"
            f"🔢 رقم الحساب (Login): `{login_val}`\n"
            f"💰 رصيد الحساب (Balance): *{balance_val}*\n"
            f"💵 الأسهم المتاحة (Equity): *{equity_val}*\n"
            f"⚙️ الرافعة المالية (Leverage): *{leverage_val}*\n\n"
            f"📈 الأصول المكتشفة بالمنصة: *{sym_count} أزواج وسلع*\n"
            f"🟡 الرمز المفتوح الآن: *{sym_key}*\n"
            f"💲 السعر المباشر الآن: `{current_p}` (الفارق: `{current_offset:+.2f}`)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"اختر الخيار المطلوب أدناه:"
        )

        keyboard = [
            [
                InlineKeyboardButton("🔄 إعادة الاتصال والمزامنة", callback_data="btn_confirm_mt5_connect"),
                InlineKeyboardButton("🎯 معايرة السعر", callback_data="btn_calibrate_price")
            ],
            [
                InlineKeyboardButton("✏️ تغيير بيانات الحساب", callback_data="btn_start_mt5_wizard"),
                InlineKeyboardButton("🔌 قطع الاتصال (Disconnect)", callback_data="btn_disconnect_mt5")
            ],
            [
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")
            ]
        ]

        await self.msg_manager.send_or_edit(bot, chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

        await self.msg_manager.send_or_edit(bot, chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

    # ─────────────────────────────────────────────
    # Other Screens
    # ─────────────────────────────────────────────

    async def _run_interactive_analysis(self, chat_id: int, bot, signal_type: str, symbol_key: str) -> None:
        """Run step-by-step loading animation before displaying signal output."""
        profile_key = self._get_user_profile(chat_id)
        loading_steps = [
            f"🔄 [1/6] Scanning live MT5 feeds for {symbol_key}...",
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
                    f"لم يتم العثور على إعداد صفقة لـ *{symbol_key}* يتوافق مع معايير نمط (*{profile_info['name']}*) حالياً.",
                    reply_markup
                )
        except Exception as e:
            logger.error(f"Interactive analysis error: {e}", exc_info=True)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء إجراء التحليل.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _run_interactive_market_analysis(self, chat_id: int, bot, symbol_key: str) -> None:
        await self.msg_manager.send_or_edit(bot, chat_id, f"📊 *{symbol_key}*:\n\n🤖 *جاري قراءة الشارت والتكات المباشرة من حساب MT5 بواسطة AI...* ⏳")
        await asyncio.sleep(0.5)
        try:
            from analytics.ai_chart_analyzer import AIChartAnalyzer
            ai_agent = AIChartAnalyzer()
            profile_key = self._get_user_profile(chat_id)
            res = await ai_agent.analyze_live_mt5_chart(symbol_key=symbol_key, timeframe='15m', selectivity_profile=profile_key)

            acc_info = res.get('account_info', {})
            login_str = acc_info.get('login', 'MT5 Live Feed')

            header = (
                f"🤖 *تحليل الشارت والبيانات المباشرة عبر AI & TradingView*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📈 الرمز: *{symbol_key}* | التغذية: `{login_str}`\n"
                f"💲 سعر TradingView المباشر: `{res.get('current_price')}`\n"
                f"📡 Bid: `{res.get('mt5_bid')}` | Ask: `{res.get('mt5_ask')}` | Spread: `{res.get('mt5_spread')}` pips\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            analysis_msg = header + res.get('ai_analysis', 'تم إكمال قراءة الشارت بنجاح.')

            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, analysis_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Interactive market analysis error: {e}", exc_info=True)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء قراءة شارت MT5 عبر الذكاء الاصطناعي.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _run_interactive_prediction(self, chat_id: int, bot, symbol_key: str) -> None:
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
        try:
            metrics = self.analytics.calculate_performance_summary(symbol=symbol)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, metrics['formatted_summary'], reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Performance display error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *خطأ في جلب تقرير الأداء.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_history(self, chat_id: int, bot) -> None:
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
        profile_key = self._get_user_profile(chat_id)
        await self.msg_manager.send_or_edit(bot, chat_id, f"🧪 *اختبار الاستراتيجية لـ {symbol_key}* ({profile_key})...\n\n🔄 Simulate candle slices & scoring validation...")
        await asyncio.sleep(0.5)
        try:
            bt_res = self.backtester.run_backtest(symbol_key=symbol_key, signal_type='SCALP', n_bars=500, profile=profile_key)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, bt_res.get('formatted_report', 'تعذر تنفيذ الاختبار'), reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Backtest execution error: {e}", exc_info=True)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء إجراء الاختبار التاريخي.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_settings(self, chat_id: int, bot) -> None:
        current_profile = self._get_user_profile(chat_id)
        profiles = Config.SELECTIVITY_PROFILES

        profile_lines = []
        for p_key, p_data in profiles.items():
            active_mark = " 👈 (مفعل حالياً)" if current_profile == p_key else ""
            profile_lines.append(
                f"• *{p_data['name']}*{active_mark}:\n"
                f"  - الحد الأدنى للتقييم: *{p_data['min_score']}/100* | أدنى عائد: *1:{p_data['min_rr']}*\n"
                f"  - _{p_data['description']}_"
            )

        text = (
            f"⚙️ *إعدادات درجة الانتقائية وأنماط التداول المتاحة*:\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            + "\n\n".join(profile_lines) + "\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"اختر درجة الانتقائية المطلوبة للتطبيق التلقائي الفوري:"
        )

        keyboard = [
            [
                InlineKeyboardButton(f"{'✅ ' if current_profile == 'SNIPER' else ''}🎯 القناص (95+)", callback_data="set_profile:SNIPER"),
                InlineKeyboardButton(f"{'✅ ' if current_profile == 'CONSERVATIVE' else ''}🛡️ المحافظ (90+)", callback_data="set_profile:CONSERVATIVE")
            ],
            [
                InlineKeyboardButton(f"{'✅ ' if current_profile == 'BALANCED' else ''}⚖️ المتوازن (82+)", callback_data="set_profile:BALANCED"),
                InlineKeyboardButton(f"{'✅ ' if current_profile == 'AGGRESSIVE' else ''}⚡ الهجومي (75+)", callback_data="set_profile:AGGRESSIVE")
            ],
            [
                InlineKeyboardButton(f"{'✅ ' if current_profile == 'ULTRA_AGGRESSIVE' else ''}🚀 الهجومي الفائق (65+)", callback_data="set_profile:ULTRA_AGGRESSIVE")
            ],
            [
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")
            ]
        ]
        await self.msg_manager.send_or_edit(bot, chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_diagnostics(self, chat_id: int, bot) -> None:
        diag_report = self.diagnostics.get_system_health_report()
        keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
        await self.msg_manager.send_or_edit(bot, chat_id, diag_report, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_status(self, chat_id: int, bot) -> None:
        try:
            if self.signal_engine:
                active = len(self.signal_engine.active_signals)
                total = self.signal_engine.total_signals
                wins = self.signal_engine.wins
                losses = self.signal_engine.losses
                total_trades = wins + losses
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                mecca_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %I:%M:%S %p بتوقيت مكة المكرمة')
            else:
                active, total, win_rate, mecca_time = 0, 0, 0, 'N/A'

            msg = self.formatter.format_status(active, total, win_rate, mecca_time)
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Show status error: {e}")
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *خطأ في جلب حالة النظام.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_interactive_help(self, chat_id: int, bot) -> None:
        help_text = """📖 المساعدة | Mustafa Bot
━━━━━━━━━━━━━━━━━━━━
📋 الأوامر المتاحة من لوحة الأزرار:

• 🔔 طلب إشارة فورية - اختيار إشارة سكالب أو سوينغ للرمز المختار
• 📊 تحليل السوق - تحليل فني مفصل لهيكل السوق والـ Order Blocks
• 🔮 توقع الأسعار - التوقعات السعرية ومناطق الارتداد
• 📈 إحصائيات الأداء - تحليل كَمّي للشخصية والأرباح والـ Sharpe
• 🔗 حساب MT5 والربط - معالج إعداد اتصال حساب التداول المباشر
• 🔄 تغيير الرمز - تغيير الزوج/السلعة الحالية (/symbol)
• ⚙️ نمط التداول - التنقل بين أنماط الانتقائية الـ 5 (Sniper ➔ Ultra Aggressive)
• 🧪 الاختبار التاريخي - فحص نتائج الاستراتيجية على البيانات التاريخية
• 🛠️ تشخيص الخادم - مراقبة حالة جلب البيانات وصحة السيرفر

⚠️ تحذير: التداول ينطوي على مخاطر عالية
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot v3.5 MT5 Integrated"""
        keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_home")]]
        await self.msg_manager.send_or_edit(bot, chat_id, help_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_price_calibration_screen(self, chat_id: int, bot) -> None:
        """Render interactive broker price calibration controls."""
        sym_key = self.user_symbols.get(chat_id, 'XAU/USD')
        from data.price_fetcher import PriceFetcher
        from data.price_calibrator import BrokerPriceCalibrator
        calibrator = BrokerPriceCalibrator()

        fetcher = PriceFetcher(sym_key)
        raw_p = fetcher._fetch_raw_current_price() or 0.0
        calibrated_p = fetcher.get_current_price(chat_id=chat_id) or raw_p
        offset = calibrator.get_user_offset(chat_id, sym_key)

        text = (
            f"🎯 *شاشة معايرة ضبط أسعار الوسيط (Broker Price Calibration)*:\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 الرمز المحدد: *{sym_key}*\n"
            f"📡 السعر الخام العام: `{raw_p:.4f}`\n"
            f"💲 السعر المعاير المعروض لك: `{calibrated_p:.4f}`\n"
            f"⚖️ الفارق المطبق حالياً: `({offset:+.4f})`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"إذا لاحظت وجود فارق بسيط بين سعر الشارت وسعر منصة وسيطك (JustMarkets)، اضغط الأزرار أدناه للتعيديل الفوري:"
        )

        keyboard = [
            [
                InlineKeyboardButton("➕ زيادة (+1.00)", callback_data="adjust_offset:1.0"),
                InlineKeyboardButton("➖ إنقاص (-1.00)", callback_data="adjust_offset:-1.0")
            ],
            [
                InlineKeyboardButton("➕ (+0.10)", callback_data="adjust_offset:0.1"),
                InlineKeyboardButton("➖ (-0.10)", callback_data="adjust_offset:-0.1")
            ],
            [
                InlineKeyboardButton("🔄 إزالة الفارق وإعادة الضبط", callback_data="adjust_offset:0.0")
            ],
            [
                InlineKeyboardButton("⬅️ العودة لإعدادات MT5", callback_data="btn_mt5_settings")
            ]
        ]
        await self.msg_manager.send_or_edit(bot, chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))
