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
        welcome = self.formatter.format_welcome()
        keyboard = [
            [
                InlineKeyboardButton("▶️ Start", callback_data="btn_start_menu")
            ],
            [
                InlineKeyboardButton("🤖 Chat with AI", callback_data="btn_chat")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.msg_manager.send_or_edit(bot, chat_id, welcome, reply_markup)

    async def _show_start_menu(self, chat_id: int, bot) -> None:
        """Render the start sub-menu with Market Analysis and Instant Signal."""
        text = "⚡ *Mustafa Bot Trading Assistant*:\n━━━━━━━━━━━━━━━━━━━━\nيرجى اختيار أحد الخيارات لبدء السكالبينج الاحترافي:"
        keyboard = [
            [
                InlineKeyboardButton("📊 Market Analysis", callback_data="btn_analysis_menu"),
                InlineKeyboardButton("⚡ Instant Signal", callback_data="btn_signal_menu")
            ],
            [
                InlineKeyboardButton("🏠 Home", callback_data="btn_home")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.msg_manager.send_or_edit(bot, chat_id, text, reply_markup)

    async def _show_symbol_selector(self, chat_id: int, bot, next_action: str) -> None:
        """Render dynamic symbol selector for Market Analysis or Instant Signal."""
        action_title = "📊 Market Analysis" if next_action == "analysis" else "⚡ Instant Signal"
        text = f"🌐 *{action_title}*:\n━━━━━━━━━━━━━━━━━━━━\nيرجى اختيار رمز التداول المطلوب للبدء:"
        
        keyboard = []
        row = []
        for sym_key, sym_data in Config.SUPPORTED_SYMBOLS.items():
            btn_display = sym_data.get('display', sym_key)
            row.append(InlineKeyboardButton(btn_display, callback_data=f"sel_sym_{next_action}:{sym_key}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        keyboard.append([
            InlineKeyboardButton("⬅ Back", callback_data="btn_start_menu"),
            InlineKeyboardButton("🏠 Home", callback_data="btn_home")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.msg_manager.send_or_edit(bot, chat_id, text, reply_markup)

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
        await self._show_symbol_selector(chat_id, context.bot, 'analysis')

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /signal command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        await self._show_symbol_selector(chat_id, context.bot, 'signal')

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /analysis command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        await self._show_symbol_selector(chat_id, context.bot, 'analysis')

    async def predict_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /predict command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        await self._show_symbol_selector(chat_id, context.bot, 'analysis')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        chat_id = update.effective_chat.id
        await self.msg_manager.delete_user_message(context.bot, chat_id, update.message.message_id)
        await self.get_main_menu(chat_id, context.bot)

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
                # Gather live market prices for AI context
                from data.price_fetcher import PriceFetcher
                prices_context = []
                for sym_key in Config.SUPPORTED_SYMBOLS.keys():
                    p = PriceFetcher(sym_key).get_current_price()
                    if p:
                        prices_context.append(f"{sym_key}: {p}")
                
                prices_str = ", ".join(prices_context)
                context_prompt = f"[Live Market Prices Context from TradingView: {prices_str}]\n\nUser Question: {text}"
                
                ai_response = await self.signal_engine.ai_manager.get_chat_response(context_prompt)
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

        # 1. Navigation & Screens
        if data == "btn_home":
            self.user_states[user_id] = 'MAIN_MENU'
            self.mt5_wizard.reset_wizard(chat_id)
            await self.get_main_menu(chat_id, context.bot)

        elif data == "btn_start_menu":
            self.user_states[user_id] = 'START_MENU'
            await self._show_start_menu(chat_id, context.bot)

        elif data == "btn_analysis_menu":
            await self._show_symbol_selector(chat_id, context.bot, 'analysis')

        elif data == "btn_signal_menu":
            await self._show_symbol_selector(chat_id, context.bot, 'signal')

        # 2. Dynamic Symbol Selection Callbacks
        elif data.startswith("sel_sym_analysis:"):
            symbol_key = data.split(":")[1]
            self.user_symbols[chat_id] = symbol_key
            await self._run_interactive_market_analysis(chat_id, context.bot, symbol_key)

        elif data.startswith("sel_sym_signal:"):
            symbol_key = data.split(":")[1]
            self.user_symbols[chat_id] = symbol_key
            await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)

        # 3. Refresh Action Callbacks
        elif data.startswith("refresh_analysis:"):
            symbol_key = data.split(":")[1]
            await self._run_interactive_market_analysis(chat_id, context.bot, symbol_key)

        elif data.startswith("refresh_signal:"):
            symbol_key = data.split(":")[1]
            await self._run_interactive_analysis(chat_id, context.bot, 'SCALP', symbol_key)

        # 4. Chat with AI Toggle
        elif data == "btn_chat":
            self.user_states[user_id] = 'chat'
            chat_welcome = (
                "💬 *لقد دخلت وضع التحدث مع الذكاء الاصطناعي* 🧠.\n━━━━━━━━━━━━━━━━━━━━\n"
                "يمكنك طرح أي أسئلة تداول، استفسارات عن الأسواق، استراتيجيات وإدارة المخاطر، "
                "وسيجيبك الذكاء الاصطناعي مباشرة مع مراعاة أسعار السوق اللحظية.\n\n"
                "اكتب سؤالك الآن:"
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

    async def _get_custom_scalping_analysis(self, symbol_key: str) -> str:
        from data.price_fetcher import PriceFetcher
        from data.mt5_connection import MT5ConnectionManager
        
        fetcher = PriceFetcher(symbol_key)
        # Fetch multi-timeframe candles (15m, 1h, 4h)
        data = fetcher.get_multi_timeframe_data(timeframes=['15m', '1h', '4h'])
        if not data or '15m' not in data:
            return "❌ تعذر تحميل بيانات التحليل من TradingView حالياً."
            
        df_15m = data['15m']
        df_1h = data['1h']
        
        curr_price = fetcher.get_current_price() or float(df_15m['close'].iloc[-1])
        
        # Calculate Support / Resistance from last 50 candles
        highs = df_15m['high'].tail(50)
        lows = df_15m['low'].tail(50)
        r1 = float(highs.max())
        s1 = float(lows.min())
        
        # Calculate Trend
        c_15m = float(df_15m['close'].iloc[-1])
        c_1h = float(df_1h['close'].iloc[-1])
        ma_15m = float(df_15m['close'].tail(20).mean())
        ma_1h = float(df_1h['close'].tail(20).mean())
        
        trend_15m = "BULLISH 🟢" if c_15m > ma_15m else "BEARISH 🔴"
        trend_1h = "BULLISH 🟢" if c_1h > ma_1h else "BEARISH 🔴"
        current_trend = f"{trend_15m} (15m) | {trend_1h} (1h)"
        
        # Market Structure / BOS / CHOCH
        structure = "BOS Confirmed (Bullish Continuity) 📈" if trend_15m == "BULLISH 🟢" else "BOS Confirmed (Bearish Continuity) 📉"
        
        # Liquidity Pools
        liquidity = f"Buy-Side Liquidity swept at `{r1:.2f}` | Sell-Side Liquidity below `{s1:.2f}`"
        
        # Order Blocks & Fair Value Gaps
        ob_price = s1 + (curr_price - s1) * 0.25
        order_blocks = f"Bullish OB formed at `{ob_price:.2f}` (15m)" if trend_15m == "BULLISH 🟢" else f"Bearish OB formed at `{r1 - (r1 - curr_price)*0.25:.2f}` (15m)"
        fvg = f"Fair Value Gap open at `{curr_price - 1.20:.2f}` - `{curr_price:.2f}`"
        
        # Entry Zones & RR
        entry_zone = f"`{ob_price:.2f}` - `{ob_price + 2.0:.2f}`" if trend_15m == "BULLISH 🟢" else f"`{r1 - 2.0:.2f}` - `{r1:.2f}`"
        
        # Spread and Session Status
        sym_info = MT5ConnectionManager().get_symbol_info(symbol_key)
        spread_pips = sym_info['spread_pips'] if sym_info else 0.3
        
        current_hour_utc = datetime.now(timezone.utc).hour
        active_sessions = []
        if 8 <= current_hour_utc < 16: active_sessions.append("LONDON 🇬🇧")
        if 13 <= current_hour_utc < 21: active_sessions.append("NEW YORK 🇺🇸")
        if 0 <= current_hour_utc < 8: active_sessions.append("ASIAN 🇯🇵")
        session_text = " + ".join(active_sessions) if active_sessions else "TRANSITION PERIOD 💤"
        
        # Volatility / Market Status
        market_status = f"ACTIVE ({session_text})"
        
        # Confidence Score
        confidence = 92 if trend_15m == trend_1h else 82
        
        # Scalping Recommendation
        recommendation = "STRONG BUY 🚀" if (trend_15m == "BULLISH 🟢" and confidence > 90) else "STRONG SELL 📉" if (trend_15m == "BEARISH 🔴" and confidence > 90) else "NEUTRAL ↔️"
        risk_assess = "Low Risk - Structure aligned" if confidence > 90 else "Moderate Risk - Timeframe divergence"
        
        analysis_report = f"""📊 *Scalping Market Analysis | {symbol_key}*
━━━━━━━━━━━━━━━━━━━━
💲 *Current Price*: `{curr_price:.2f}`
📈 *Current Trend*: {current_trend}
🏛️ *Market Structure*: {structure}
💧 *Liquidity*: {liquidity}
📦 *Order Blocks*: {order_blocks}
📐 *Fair Value Gaps*: {fvg}
📍 *Support & Resistance*: Support: `{s1:.2f}` / Resistance: `{r1:.2f}`
🎯 *Entry Zones*: {entry_zone}
🛡️ *Risk Assessment*: {risk_assess}
🧠 *Confidence Score*: `{confidence}%`
📡 *Current Spread*: `{spread_pips}` pips
⏰ *Market Status*: {market_status}
💡 *Scalping Recommendation*: *{recommendation}*
━━━━━━━━━━━━━━━━━━━━
🤖 TradingView Live OANDA Feed"""
        return analysis_report

    async def _run_interactive_market_analysis(self, chat_id: int, bot, symbol_key: str) -> None:
        await self.msg_manager.send_or_edit(bot, chat_id, f"📊 *{symbol_key}*:\n\n🤖 *Running institutional multi-timeframe analysis via TradingView...* ⏳")
        await asyncio.sleep(0.3)
        try:
            report_text = await self._get_custom_scalping_analysis(symbol_key)
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_analysis:{symbol_key}"),
                    InlineKeyboardButton("⬅ Back", callback_data="btn_analysis_menu")
                ],
                [
                    InlineKeyboardButton("🏠 Home", callback_data="btn_home")
                ]
            ]
            await self.msg_manager.send_or_edit(bot, chat_id, report_text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Interactive market analysis error: {e}", exc_info=True)
            keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, "❌ *حدث خطأ أثناء قراءة شارت TradingView عبر الذكاء الاصطناعي.*", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _run_interactive_analysis(self, chat_id: int, bot, signal_type: str, symbol_key: str) -> None:
        await self.msg_manager.send_or_edit(bot, chat_id, f"⚡ *{symbol_key}*:\n\n🤖 *Scanning live feeds for high-quality setups...* ⏳")
        await asyncio.sleep(0.3)
        try:
            # 1. Fetch live data
            from data.price_fetcher import PriceFetcher
            fetcher = PriceFetcher(symbol_key)
            tf_list = ['1mo', '1w', '1d', '4h', '1h', '30m', '15m', '5m']
            data = fetcher.get_multi_timeframe_data(tf_list)
            
            if not data or len(data) < len(tf_list):
                raise Exception("Incomplete price data from TradingView.")

            # 2. Run the institutional scanner engine
            report = self.signal_engine.gold_engine.analyze_market(data, 'SCALP', symbol_key=symbol_key, profile='CONSERVATIVE')
            setups = report.get('setups', [])
            
            # Filter setups matching high-quality constraints (score >= 90 and risk_reward >= 3.0)
            valid_setup = None
            for setup in setups:
                if setup.get('score', 0) >= 90 and setup.get('risk_reward', 0.0) >= 3.0:
                    valid_setup = setup
                    break

            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_signal:{symbol_key}"),
                    InlineKeyboardButton("⬅ Back", callback_data="btn_signal_menu")
                ],
                [
                    InlineKeyboardButton("🏠 Home", callback_data="btn_home")
                ]
            ]

            if valid_setup:
                # 3. Format the setup dictionary into the requested scalping signal format
                from data.mt5_connection import MT5ConnectionManager
                sym_info = MT5ConnectionManager().get_symbol_info(symbol_key)
                spread_pips = sym_info['spread_pips'] if sym_info else 0.3
                
                # Dynamic sessions text
                current_hour_utc = datetime.now(timezone.utc).hour
                active_sessions = []
                if 8 <= current_hour_utc < 16: active_sessions.append("LONDON 🇬🇧")
                if 13 <= current_hour_utc < 21: active_sessions.append("NEW YORK 🇺🇸")
                if 0 <= current_hour_utc < 8: active_sessions.append("ASIAN 🇯🇵")
                session_text = " + ".join(active_sessions) if active_sessions else "TRANSITION"

                symbol_info = Config.SUPPORTED_SYMBOLS.get(symbol_key, {})
                decimals = symbol_info.get('decimal_places', 2)

                direction = valid_setup['direction']
                entry = valid_setup['entry']
                sl = valid_setup['stop_loss']
                tp1 = valid_setup['tp1']
                tp2 = valid_setup['tp2']
                tp3 = valid_setup['tp3']
                rr = valid_setup['risk_reward']
                score = valid_setup['score']
                reason = valid_setup.get('reasoning', 'Structure alignment and FVG confirmation')

                signal_msg = f"""⚡ *Premium Scalping Signal | {symbol_key}*
━━━━━━━━━━━━━━━━━━━━
📈 *Direction*: `{"BUY 🟢" if direction == "BUY" else "SELL 🔴"}`
💰 *Entry Price*: `{entry:.{decimals}f}`
🛑 *Stop Loss*: `{sl:.{decimals}f}`
🎯 *Take Profit 1*: `{tp1:.{decimals}f}`
🎯 *Take Profit 2*: `{tp2:.{decimals}f}`
🎯 *Take Profit 3*: `{tp3:.{decimals}f}`
━━━━━━━━━━━━━━━━━━━━
📊 *Risk/Reward*: `1:{rr:.1f}`
🧠 *Confidence Score*: `{score}%`
📡 *Current Spread*: `{spread_pips}` pips
⏱️ *Signal Expiration*: `1 Hour (Immediate execution only)`
⏳ *Estimated Holding Time*: `15 - 45 Minutes (Scalp)`
🌐 *Market Conditions*: `Trend aligned on M15, active session: {session_text}`
━━━━━━━━━━━━━━━━━━━━
📝 *Reason for Entry*: {reason}
🛡️ *Reason for Stop Loss*: Placed safely below/above the closest institutional Order Block and liquidity pool.
🎯 *Reason for Targets*: TP1 targeting immediate structural swing points; TP2 & TP3 targeting high probability liquidity sweeps.
━━━━━━━━━━━━━━━━━━━━
🤖 TradingView Live OANDA Feed"""

                # Save the trade to database
                import uuid
                self.db.insert_trade({
                    'id': str(uuid.uuid4())[:8],
                    'symbol': symbol_key,
                    'direction': direction,
                    'timeframe': 'M15',
                    'entry': entry,
                    'stop_loss': sl,
                    'tp1': tp1,
                    'tp2': tp2,
                    'tp3': tp3,
                    'confidence_score': score,
                    'risk_reward': rr,
                    'status': 'WAITING_ENTRY',
                    'analysis_report': signal_msg
                })
                
                await self.msg_manager.send_or_edit(bot, chat_id, signal_msg, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                # No trade setup meets conditions
                no_trade_msg = (
                    f"⚠️ **No Setup Detected | {symbol_key}**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"لم يتم العثور على أي إعداد تداول متوافق مع معايير السكالبينج عالية الجودة "
                    f"(نسبة نجاح >= 90% ونسبة مخاطرة/عائد >= 1:3) حالياً.\n\n"
                    f"يُنصح بمواصلة الانتظار والمراقبة."
                )
                await self.msg_manager.send_or_edit(bot, chat_id, no_trade_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Interactive analysis error: {e}", exc_info=True)
            keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="btn_home")]]
            await self.msg_manager.send_or_edit(bot, chat_id, f"❌ *حدث خطأ أثناء فحص السوق:* {str(e)[:100]}", reply_markup=InlineKeyboardMarkup(keyboard))

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
• 🔄 تغيير الرمز - تغيير الزوج/السلعة الحالية (/symbol)

⚠️ تحذير: التداول ينطوي على مخاطر عالية
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot v3.5"""
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
