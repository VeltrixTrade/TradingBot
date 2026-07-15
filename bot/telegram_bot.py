"""
Mustafa Bot - Telegram Bot & Signal Engine
المحرك الرئيسي وبوت تلجرام
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import Config
from bot.commands import BotCommands
from bot.formatters import MessageFormatter
from data.price_fetcher import PriceFetcher
from analysis.smc_ict import SMCICTEngine
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

        self.price_fetcher = PriceFetcher(Config.SYMBOL, Config.EXCHANGE)
        self.smc_engine = SMCICTEngine()
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

    async def run_analysis(self, signal_type: str = 'SCALP') -> List[Signal]:
        """Run complete analysis pipeline."""
        try:
            logger.info(f'🔄 Starting {signal_type} analysis...')

            # 1. Fetch data
            timeframes = Config.SCALP_TIMEFRAMES if signal_type == 'SCALP' else Config.SWING_TIMEFRAMES
            # Always include higher TFs for context
            all_tfs = list(set(timeframes + ['1h', '4h']))

            data = self.price_fetcher.get_multi_timeframe_data(all_tfs)

            if not data:
                logger.warning('No price data available')
                return []

            current_price = self.price_fetcher.get_current_price()
            if current_price is None:
                logger.warning('Cannot get current price')
                return []

            # 2. Multi-timeframe SMC/ICT analysis
            mtf_analysis = self.smc_engine.multi_timeframe_analysis(data)
            higher_tf_bias = mtf_analysis.get('higher_tf_bias', 'NEUTRAL')

            # Use the primary timeframe analysis
            primary_tf = timeframes[-1] if timeframes else '15m'
            if primary_tf in mtf_analysis.get('analyses', {}):
                smc_analysis = mtf_analysis['analyses'][primary_tf]
            elif data:
                first_tf = list(data.keys())[0]
                smc_analysis = self.smc_engine.analyze(data[first_tf], first_tf)
            else:
                return []

            # 3. AI consensus
            market_data = {'current_price': current_price, 'timeframes': list(data.keys())}
            ai_consensus = await self.ai_manager.get_consensus_analysis(
                market_data, smc_analysis, signal_type
            )

            # 4. Generate signals
            tf_label = primary_tf.upper()
            signals = self.signal_generator.generate_signals(
                smc_analysis, ai_consensus, signal_type, tf_label, current_price
            )

            # 5. Filter signals
            filtered = self.signal_filter.filter_signals(
                signals,
                market_trend=higher_tf_bias,
            )

            if filtered:
                self.active_signals.extend(filtered)
                self.total_signals += len(filtered)
                logger.info(f'✅ {len(filtered)} {signal_type} signal(s) ready to send')

            return filtered

        except Exception as e:
            logger.error(f'Analysis pipeline error: {e}', exc_info=True)
            return []

    async def get_market_analysis(self) -> str:
        """Get formatted market analysis text."""
        try:
            data = self.price_fetcher.get_multi_timeframe_data(['15m', '1h', '4h'])
            if not data:
                return '❌ لا يمكن جلب بيانات السوق حالياً'

            current_price = self.price_fetcher.get_current_price() or 0

            # Analyze primary timeframe
            primary_tf = '1h' if '1h' in data else list(data.keys())[0]
            analysis = self.smc_engine.analyze(data[primary_tf], primary_tf)

            return self.formatter.format_analysis(
                analysis.get('summary', 'لا يوجد تحليل'),
                current_price,
                analysis.get('overall_bias', 'NEUTRAL'),
            )

        except Exception as e:
            logger.error(f'Market analysis error: {e}')
            return f'❌ خطأ في التحليل: {str(e)[:100]}'

    async def get_prediction(self) -> str:
        """Get formatted prediction text."""
        try:
            data = self.price_fetcher.get_multi_timeframe_data(['1h', '4h', '1d'])
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
        self.app: Optional[Application] = None
        self.chat_id = Config.CHAT_ID
        self._analysis_running = False

    async def send_signal(self, signal: Signal) -> None:
        """Send a signal to the configured chat."""
        try:
            if self.app and self.chat_id:
                msg = MessageFormatter.format_signal(signal)
                await self.app.bot.send_message(
                    chat_id=self.chat_id,
                    text=msg,
                )
                logger.info(f'📤 Signal {signal.id} sent to {self.chat_id}')
        except Exception as e:
            logger.error(f'Error sending signal: {e}')

    async def scheduled_analysis(self) -> None:
        """Run scheduled analysis and send signals if found."""
        if self._analysis_running:
            return

        self._analysis_running = True

        try:
            # Check if in kill zone
            if not AnalysisScheduler.is_kill_zone():
                logger.debug('Outside kill zones, skipping analysis')
                return

            kill_zone = AnalysisScheduler.get_active_kill_zone()
            logger.info(f'⏰ Running scheduled analysis (Kill Zone: {kill_zone})')

            # Run scalp analysis
            scalp_signals = await self.engine.run_analysis('SCALP')
            for signal in scalp_signals:
                await self.send_signal(signal)

            # Run swing analysis (less frequently)
            current_minute = datetime.now(timezone.utc).minute
            if current_minute < 5:  # Only at the top of each hour
                swing_signals = await self.engine.run_analysis('SWING')
                for signal in swing_signals:
                    await self.send_signal(signal)

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

    async def post_shutdown(self, application: Application) -> None:
        """Runs during bot shutdown."""
        if hasattr(self, 'scheduler') and self.scheduler:
            self.scheduler.stop()
            logger.info('⏰ Scheduler stopped')

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
        self.app.add_handler(CommandHandler('signal', self.commands.signal_command))
        self.app.add_handler(CommandHandler('analysis', self.commands.analysis_command))
        self.app.add_handler(CommandHandler('predict', self.commands.predict_command))
        self.app.add_handler(CommandHandler('status', self.commands.status_command))
        self.app.add_handler(CommandHandler('help', self.commands.help_command))

        # Add text message handler for custom keyboard buttons
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.commands.handle_message))

        logger.info('✅ Bot handlers configured')


