"""
Mustafa Bot - Telegram Bot & Signal Engine
المحرك الرئيسي وبوت تلجرام
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import Config
from bot.commands import BotCommands
from bot.formatters import MessageFormatter
from data.price_fetcher import PriceFetcher
from analysis.smc_ict import SMCICTEngine
from analysis.gold_engine import GoldMarketAnalysisEngine
from ai.ai_manager import AIManager
from signals.signal_generator import SignalGenerator
from signals.signal_filter import SignalFilter
from signals.models import Signal
from utils.scheduler import AnalysisScheduler

logger = logging.getLogger('mustafa_bot.bot')


class SignalEngine:
    """Orchestrates the complete analysis pipeline."""

    def __init__(self):
        logger.info('Initializing Signal Engine...')

        self.price_fetchers = {}
        self.smc_engine = SMCICTEngine()
        self.gold_engine = GoldMarketAnalysisEngine()
        self.ai_manager = AIManager(
            Config.DEEPSEEK_API_KEY,
            Config.GEMINI_API_KEY,
            Config.OPENAI_API_KEY,
            Config.DEEPSEEK_MODEL,
            Config.GEMINI_MODEL,
            Config.OPENAI_MODEL,
        )
        self.signal_generator = SignalGenerator()
        self.signal_filter = SignalFilter()
        self.formatter = MessageFormatter()

        self.active_signals: List[Signal] = []
        self.total_signals: int = 0
        self.wins: int = 0
        self.losses: int = 0

        logger.info('✅ Signal Engine initialized')

    def get_fetcher(self, symbol_key: str) -> PriceFetcher:
        """Get or create PriceFetcher for the symbol key."""
        if symbol_key not in self.price_fetchers:
            self.price_fetchers[symbol_key] = PriceFetcher(symbol_key)
        return self.price_fetchers[symbol_key]

    async def run_analysis(self, signal_type: str = 'SCALP', is_manual: bool = False, symbol_key: str = 'XAU/USD', profile: str = 'AGGRESSIVE') -> List[Signal]:
        """Run complete institutional multi-timeframe analysis pipeline for a specific symbol."""
        try:
            from database.db_manager import DatabaseManager
            db = DatabaseManager()
            target_score = db.get_setting('min_score', '75')
            logger.info(f'🔄 Starting institutional {signal_type} analysis for {symbol_key} (Manual: {is_manual}, MinScore: {target_score}%)...')

            # 1. Fetch available timeframes
            tf_list = ['1mo', '1w', '1d', '4h', '1h', '30m', '15m', '5m']
            fetcher = self.get_fetcher(symbol_key)
            data = fetcher.get_multi_timeframe_data(tf_list)

            # Essential execution timeframes required for analysis
            required_tfs = ['15m', '1h', '4h']
            missing_req = [tf for tf in required_tfs if tf not in data]

            if not data or missing_req:
                logger.warning(f'Essential price data missing for {symbol_key}. Missing: {missing_req}')
                db.insert_rejected_signal(symbol_key, "NONE", 0, 0.0, "REJECTED_MISSING_DATA", f"Missing essential timeframes: {missing_req}")
                return []

            # 2. Run institutional analysis engine
            report = self.gold_engine.analyze_market(data, signal_type, symbol_key=symbol_key, profile=profile)
            setups = report.get('setups', [])

            if not setups:
                logger.info(f'No setups passing score filter for {symbol_key} ({signal_type}, TargetScore: {target_score}%)')
                db.insert_rejected_signal(symbol_key, "NONE", 0, 0.0, "REJECTED_NO_QUALIFIED_SETUPS", f"Gold engine found zero setups matching target threshold ({target_score}%)")
                return []

            # Convert setups to Signal models & Register to Database
            from signals.models import Direction as ModelDirection, SignalType as ModelSignalType
            from database.db_manager import DatabaseManager
            import uuid

            db = DatabaseManager()
            filtered = []

            for setup in setups:
                direction_val = ModelDirection.BUY if setup['direction'] == 'BUY' else ModelDirection.SELL
                sig_type_val = ModelSignalType.SCALP if signal_type == 'SCALP' else ModelSignalType.SWING
                exec_tf = '15m' if signal_type == 'SCALP' else '1h'

                # Pre-format the institutional report
                formatted_report = MessageFormatter.format_institutional_signal(setup)

                sig_id = str(uuid.uuid4())[:8]
                from signals.models import OrderType, SignalStatus
                order_type_obj = setup.get('order_type', OrderType.MARKET_BUY)
                status_obj = SignalStatus.PENDING if setup.get('status') == 'PENDING' else SignalStatus.ACTIVE

                signal = Signal(
                    id=sig_id,
                    type=sig_type_val,
                    direction=direction_val,
                    order_type=order_type_obj,
                    entry=setup['entry'],
                    stop_loss=setup['stop_loss'],
                    take_profit_1=setup['tp1'],
                    take_profit_2=setup['tp2'],
                    take_profit_3=setup['tp3'],
                    risk_reward=setup['risk_reward'],
                    confidence=setup['score'],
                    timeframe=exec_tf.upper(),
                    expiration_time=setup.get('expiration_time', ''),
                    estimated_holding_time=setup.get('holding_time', ''),
                    entry_reasons=setup.get('reasons_entry', ''),
                    sl_reasons=setup.get('sl_reasons', ''),
                    tp_reasons=setup.get('tp_reasons', ''),
                    smc_setup=setup['structure_analysis'],
                    ai_consensus=setup['institutional_confirmation'],
                    ai_agreement=3,
                    analysis_text=formatted_report,
                    prediction=setup.get('reasoning', ''),
                    reversal_zones=[],
                    status=status_obj
                )
                filtered.append(signal)

                # Save accepted trade/pending order to SQLite database for active lifecycle tracking
                trade_record = {
                    'id': sig_id,
                    'symbol': symbol_key,
                    'direction': setup['direction'],
                    'order_type': setup.get('order_type_str', 'MARKET_BUY'),
                    'entry': setup['entry'],
                    'stop_loss': setup['stop_loss'],
                    'tp1': setup['tp1'],
                    'tp2': setup['tp2'],
                    'tp3': setup['tp3'],
                    'timeframe': exec_tf.upper(),
                    'confidence_score': setup['score'],
                    'risk_reward': setup['risk_reward'],
                    'status': setup.get('status', 'PENDING'),
                    'expiration_time': setup.get('expiration_time', ''),
                    'analysis_report': formatted_report,
                    'result': 'PENDING'
                }
                db.insert_trade(trade_record)

            # 3. Prevent duplicates and prune active signals (keep only last 24 hours)
            if filtered:
                self.active_signals = [
                    s for s in self.active_signals
                    if (datetime.utcnow() - s.created_at.replace(tzinfo=None)).total_seconds() < 86400
                ]

                unique_signals = []
                for sig in filtered:
                    is_duplicate = False
                    for active_sig in self.active_signals:
                        price_diff = abs(sig.entry - active_sig.entry)
                        time_diff = (datetime.utcnow() - active_sig.created_at.replace(tzinfo=None)).total_seconds()
                        
                        # Duplicate criteria: same direction, timeframe, close entry (within 2.0 dollars), and within last 2 hours
                        if (sig.direction == active_sig.direction and 
                            sig.timeframe == active_sig.timeframe and 
                            price_diff < 2.0 and 
                            time_diff < 7200):
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        unique_signals.append(sig)

                filtered = unique_signals

            if filtered:
                self.active_signals.extend(filtered)
                self.total_signals += len(filtered)
                logger.info(f'✅ {len(filtered)} {symbol_key} {signal_type} unique signal(s) ready to send')

            return filtered

        except Exception as e:
            logger.error(f'Institutional analysis pipeline error: {e}', exc_info=True)
            return []

    async def get_market_analysis(self, symbol_key: str = 'XAU/USD') -> str:
        """Get formatted market analysis text with Multi-Timeframe Trend Dashboard for a specific symbol."""
        try:
            fetcher = self.get_fetcher(symbol_key)
            data = fetcher.get_multi_timeframe_data(['15m', '1h', '4h'])
            if not data:
                return '❌ لا يمكن جلب بيانات السوق حالياً'

            current_price = fetcher.get_current_price() or 0

            # Perform MTF analysis
            mtf_result = self.smc_engine.multi_timeframe_analysis(data)
            analyses = mtf_result.get('analyses', {})

            # Extract trends
            tfs = {'15m': 'NEUTRAL', '1h': 'NEUTRAL', '4h': 'NEUTRAL'}
            for tf_key in tfs.keys():
                if tf_key in analyses:
                    tfs[tf_key] = analyses[tf_key].get('overall_bias', 'NEUTRAL')

            # Formulate icons
            def get_trend_icon(t_val: str) -> str:
                return 'صاعد 🟢' if t_val == 'BULLISH' else 'هابط 🔴' if t_val == 'BEARISH' else 'حيادي 🟡'

            t15 = get_trend_icon(tfs['15m'])
            t1h = get_trend_icon(tfs['1h'])
            t4h = get_trend_icon(tfs['4h'])

            # Harmony check
            if tfs['15m'] == tfs['1h'] == tfs['4h'] == 'BULLISH':
                harmony = "🟢 تناسق شرائي كامل (صعود موحد على كافة الفريمات)"
            elif tfs['15m'] == tfs['1h'] == tfs['4h'] == 'BEARISH':
                harmony = "🔴 تناسق بيعي كامل (هبوط موحد على كافة الفريمات)"
            elif tfs['1h'] == tfs['4h'] != 'NEUTRAL':
                harmony = f"🔄 اتجاه عام موحد ({get_trend_icon(tfs['1h'])})، فريم السكالب متذبذب"
            else:
                harmony = "⚠️ تعارض اتجاهي بين الفريمات (يُنصح بالتداول بحذر وانتظار الاستقرار)"

            mtf_dashboard = f"""🌍 لوحة الاتجاهات متعددة الأطر (MTF Dashboard) - {symbol_key}:
  • 15m (إطار السكالب): {t15}
  • 1h  (الإطار اليومي): {t1h}
  • 4h  (إطار الاتجاه): {t4h}
  • توافق الاتجاه: {harmony}
━━━━━━━━━━━━━━━━━━━━"""

            # Analyze primary timeframe for details (1h)
            primary_tf = '1h' if '1h' in data else list(data.keys())[0]
            primary_analysis = analyses.get(primary_tf, self.smc_engine.analyze(data[primary_tf], primary_tf))
            primary_summary = primary_analysis.get('summary', 'لا يوجد تحليل مفصل')

            # Prepend dashboard to the summary
            summary_with_dashboard = f"{mtf_dashboard}\n\n{primary_summary}"

            return self.formatter.format_analysis(
                summary_with_dashboard,
                current_price,
                primary_analysis.get('overall_bias', 'NEUTRAL'),
            )

        except Exception as e:
            logger.error(f'Market analysis error: {e}', exc_info=True)
            return f'❌ خطأ في التحليل: {str(e)[:100]}'

    async def get_prediction(self, symbol_key: str = 'XAU/USD') -> str:
        """Get formatted prediction text for a specific symbol."""
        try:
            fetcher = self.get_fetcher(symbol_key)
            data = fetcher.get_multi_timeframe_data(['1h', '4h', '1d'])
            if not data:
                return '❌ لا يمكن جلب البيانات'

            primary_tf = '4h' if '4h' in data else list(data.keys())[0]
            analysis = self.smc_engine.analyze(data[primary_tf], primary_tf)
            market_data = {'current_price': analysis['current_price']}

            prediction_result = await self.ai_manager.get_prediction(market_data, analysis)

            return self.formatter.format_prediction(
                prediction_result.get('prediction', ''),
                prediction_result.get('reversal_zones', []),
            )

        except Exception as e:
            logger.error(f'Prediction error: {e}')
            return f'❌ خطأ في التوقع: {str(e)[:100]}'


class MustafaBot:
    """Main Telegram bot class."""

    def __init__(self):
        self.engine = SignalEngine()
        self.commands = BotCommands(self.engine)
        from trade_management.lifecycle import TradeLifecycleEngine
        from scalping.fast_scanner import FastMarketScanner
        
        self.lifecycle_engine = TradeLifecycleEngine()
        self.lifecycle_engine.set_notification_callback(self.on_trade_lifecycle_update)

        self.fast_scanner = FastMarketScanner()
        self.fast_scanner.set_notification_callback(self.on_fast_scanner_signal)

        self.app: Optional[Application] = None
        self.chat_id = Config.CHAT_ID
        self._analysis_running = False

    async def broadcast_signal_to_users(self, msg_text: str) -> None:
        """Broadcast signal EXCLUSIVELY to the linked Telegram channel."""
        if not self.app:
            return

        # Send exclusively to the linked Telegram channel / chat ID
        if self.chat_id and str(self.chat_id).strip() not in ('0', ''):
            try:
                await self.app.bot.send_message(chat_id=self.chat_id, text=msg_text, parse_mode="Markdown")
                logger.info(f"📤 Signal broadcasted exclusively to linked channel ({self.chat_id})")
            except Exception as e:
                logger.error(f"Error sending signal to linked channel {self.chat_id}: {e}")
        else:
            logger.warning("⚠️ No linked Telegram channel ID configured (TELEGRAM_CHAT_ID / TELEGRAM_CHANNEL_ID)")

    async def on_fast_scanner_signal(self, setup: dict) -> None:
        """Broadcast instant winning scalping setup immediately to all users."""
        try:
            msg = MessageFormatter.format_institutional_signal(setup)
            await self.broadcast_signal_to_users(msg)
            logger.info(f"⚡ Instant Scalper Signal published to users: {setup['symbol']} ({setup.get('strategy_name')})")
        except Exception as e:
            logger.error(f"Error publishing fast scanner signal: {e}")

    async def on_trade_lifecycle_update(self, trade: dict, old_status: str, new_status: str, price: float, notes: str) -> None:
        """Broadcast clean trade lifecycle updates (Entry, TP1, TP2, TP3, SL) to active subscribers."""
        try:
            symbol = trade['symbol']
            
            if new_status == 'TP1_HIT':
                msg = f"🎯 *تحقيق الهدف الأول (TP1)* | *{symbol}*\n━━━━━━━━━━━━━━━━━━━━\n💰 *السعر الحالي*: `{price:.4f}`\n🛡️ *تنبيه الخطة*: تم تحريك حد الوقف إلى سعر الدخول تلقائياً (Break-Even)."
            elif new_status == 'TP2_HIT':
                msg = f"🎯 *تحقيق الهدف الثاني (TP2)* | *{symbol}*\n━━━━━━━━━━━━━━━━━━━━\n💰 *السعر الحالي*: `{price:.4f}`"
            elif new_status == 'TP3_HIT':
                msg = f"🏁 *تحقيق الهدف الثالث الكامل (TP3)* | *{symbol}*\n━━━━━━━━━━━━━━━━━━━━\n💰 *السعر الحالي*: `{price:.4f}`\n✅ اكتملت الصفقة بنجاح كاسح وحققت كافة الأهداف!"
            elif new_status == 'SL_HIT':
                msg = f"🛑 *إصابة حد وقف الخسارة (SL)* | *{symbol}*\n━━━━━━━━━━━━━━━━━━━━\n💰 *السعر الحالي*: `{price:.4f}`"
            elif new_status in ['ENTRY_EXECUTED', 'ACTIVE']:
                msg = f"⚡ *تفعيل أمر الصفقة* | *{symbol}*\n━━━━━━━━━━━━━━━━━━━━\n💰 *سعر التفعيل*: `{price:.4f}`"
            elif new_status in ['CANCELLED_INVALIDATED', 'EXPIRED']:
                msg = f"🚫 *إلغاء الأمر المعلق* | *{symbol}*\n━━━━━━━━━━━━━━━━━━━━\n📝 *البيان*: {notes}"
            else:
                return

            await self.broadcast_signal_to_users(msg)
        except Exception as e:
            logger.error(f"Error sending trade lifecycle notification: {e}")

    async def send_signal(self, signal: Signal) -> None:
        """Send a signal to the configured chat and active users."""
        try:
            msg = MessageFormatter.format_signal(signal)
            await self.broadcast_signal_to_users(msg)
            logger.info(f'📤 Signal {signal.id} broadcasted successfully.')
        except Exception as e:
            logger.error(f'Error sending signal: {e}')

    async def scheduled_analysis(self) -> None:
        """Run scheduled analysis and send signals if found for symbols without active trades."""
        if self._analysis_running:
            return

        self._analysis_running = True

        try:
            kill_zone = AnalysisScheduler.get_active_kill_zone() or "None (Continuous Scan)"
            logger.info(f'⏰ Running scheduled analysis (Kill Zone: {kill_zone})')

            from database.db_manager import DatabaseManager
            db = DatabaseManager()
            active_trades = db.get_active_trades()
            active_symbols = {t['symbol'] for t in active_trades}

            async def analyze_and_publish(sym_key):
                if sym_key in active_symbols:
                    logger.info(f"⏳ Skipping scheduled scan for {sym_key} (Active trade already managed)")
                    return

                # Run scalp analysis
                scalp_signals = await self.engine.run_analysis('SCALP', symbol_key=sym_key)
                for signal in scalp_signals:
                    await self.send_signal(signal)

                # Run swing analysis (less frequently)
                current_minute = datetime.now(timezone.utc).minute
                if current_minute < 5:  # Only at the top of each hour
                    swing_signals = await self.engine.run_analysis('SWING', symbol_key=sym_key)
                    for signal in swing_signals:
                        await self.send_signal(signal)

            symbols = list(Config.SUPPORTED_SYMBOLS.keys())
            tasks = [analyze_and_publish(sym) for sym in symbols]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f'Scheduled analysis error: {e}', exc_info=True)
        finally:
            self._analysis_running = False

    async def post_init(self, application: Application) -> None:
        """Runs after the bot is initialized and event loop is running."""
        # Initialize and start scheduler inside the event loop
        self.scheduler = AnalysisScheduler()
        self.scheduler.add_analysis_job(self.scheduled_analysis, Config.ANALYSIS_INTERVAL_SECONDS)
        self.scheduler.start()
        logger.info(f'⏰ Scheduler configured and started: every {Config.ANALYSIS_INTERVAL_SECONDS}s')

        # Start trade lifecycle async background loop
        asyncio.create_task(self.lifecycle_engine.start_worker_loop(15))
        logger.info('⏰ Trade Lifecycle Worker loop task initialized')

        # Start continuous ultra-fast market scanner background loop
        asyncio.create_task(self.fast_scanner.start_continuous_scanner_loop(10))
        logger.info('⚡ Continuous Fast Market Scanner worker task initialized')

    async def post_shutdown(self, application: Application) -> None:
        """Runs during bot shutdown."""
        if hasattr(self, 'scheduler') and self.scheduler:
            self.scheduler.stop()
            logger.info('⏰ Scheduler stopped')

        if hasattr(self, 'lifecycle_engine') and self.lifecycle_engine:
            self.lifecycle_engine.stop_worker_loop()
            logger.info('⏰ Trade Lifecycle Worker stopped')

    def setup(self) -> None:
        """Setup the bot with all command handlers."""
        self.app = (
            Application.builder()
            .token(Config.TELEGRAM_TOKEN)
            .post_init(self.post_init)
            .post_shutdown(self.post_shutdown)
            .build()
        )

        # Add command handlers
        self.app.add_handler(CommandHandler('start', self.commands.start_command))
        self.app.add_handler(CommandHandler('cancel', self.commands.cancel_command))
        self.app.add_handler(CommandHandler('signal', self.commands.signal_command))
        self.app.add_handler(CommandHandler('analysis', self.commands.analysis_command))
        self.app.add_handler(CommandHandler('predict', self.commands.predict_command))
        self.app.add_handler(CommandHandler('status', self.commands.status_command))
        self.app.add_handler(CommandHandler('help', self.commands.help_command))
        self.app.add_handler(CommandHandler('symbol', self.commands.symbol_command))

        # Add text message handler for custom keyboard buttons and AI chat
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.commands.handle_message))

        # Add inline button callback handler
        self.app.add_handler(CallbackQueryHandler(self.commands.handle_callback))

        logger.info('✅ Bot handlers configured')



