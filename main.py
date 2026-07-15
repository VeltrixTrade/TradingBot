"""
🤖 Mustafa Bot - Gold Trading Signals
نقطة الدخول الرئيسية
━━━━━━━━━━━━━━━━━━━━
Strategy: SMC + ICT
AI: DeepSeek + Gemini + ChatGPT
Data: TradingView
━━━━━━━━━━━━━━━━━━━━
"""

import sys
import logging
from config import Config
from utils.logger import setup_logging


def main():
    """Main entry point for Mustafa Bot."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger('mustafa_bot')

    # Print banner
    logger.info('=' * 55)
    logger.info('🤖  MUSTAFA BOT - Gold Trading Signals')
    logger.info('=' * 55)
    logger.info('📊  Strategy : SMC + ICT')
    logger.info('🧠  AI       : DeepSeek + Gemini + ChatGPT')
    logger.info('📈  Asset    : XAUUSD (Gold)')
    logger.info('📡  Data     : TradingView + yfinance')
    logger.info('🔍  Filter   : 5-Stage Pipeline')
    logger.info('=' * 55)

    # Validate config
    errors = Config.validate()
    if errors:
        logger.error('❌ Configuration errors found:')
        for error in errors:
            logger.error(f'   • {error}')
        logger.error('')
        logger.error('Please set the required environment variables.')
        logger.error('See .env.example for reference.')
        sys.exit(1)

    logger.info('✅ Configuration validated')

    # Import here to avoid circular imports and show config errors first
    from bot.telegram_bot import MustafaBot

    # Create bot
    bot = MustafaBot()
    bot.setup()
    logger.info('✅ Bot configured')

    # Start
    logger.info('')
    logger.info('🚀 Starting Mustafa Bot...')
    logger.info('📱 Send /start to your bot on Telegram')
    logger.info('')

    # Start bot (blocking)
    try:
        bot.app.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query'],
        )
    except KeyboardInterrupt:
        logger.info('🛑 Shutdown requested by user')
    except Exception as e:
        logger.error(f'❌ Fatal error: {e}', exc_info=True)
    finally:
        logger.info('👋 Mustafa Bot stopped. Goodbye!')



if __name__ == '__main__':
    main()
