"""
Mustafa Bot - Logging Configuration
نظام تسجيل متكامل مع ملف وكونسول
"""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for Mustafa Bot."""
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    log_format = '%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    root_logger = logging.getLogger('mustafa_bot')
    root_logger.setLevel(level)

    # Prevent duplicate handlers
    if root_logger.handlers:
        return

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    # File handler
    try:
        file_handler = logging.FileHandler('mustafa_bot.log', encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
        root_logger.addHandler(file_handler)
    except Exception:
        root_logger.warning('Could not create log file, logging to console only')

    # Reduce noise from third-party libs
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the mustafa_bot prefix."""
    return logging.getLogger(f'mustafa_bot.{name}')
