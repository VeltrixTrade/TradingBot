"""
Mustafa Bot - Analysis Scheduler
جدولة التحليل التلقائي خلال ساعات التداول النشطة
"""

import logging
from datetime import datetime, timezone
from typing import Callable, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger('mustafa_bot.scheduler')


class AnalysisScheduler:
    """Manages scheduled analysis jobs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone='UTC')
        self._running = False

    def start(self) -> None:
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info('⏰ Scheduler started')

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info('⏰ Scheduler stopped')

    def add_analysis_job(self, callback: Callable, interval_seconds: int = 60) -> None:
        """Add a recurring analysis job."""
        self.scheduler.add_job(
            callback,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id='analysis_job',
            name='Market Analysis',
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f'Analysis job added: every {interval_seconds}s')

    def add_daily_report_job(self, callback: Callable, hour: int = 20, minute: int = 0) -> None:
        """Add a daily report job at specified UTC hour."""
        self.scheduler.add_job(
            callback,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_report',
            name='Daily Report',
            replace_existing=True,
        )
        logger.info(f'Daily report job added: {hour:02d}:{minute:02d} UTC')

    @staticmethod
    def is_kill_zone() -> bool:
        """Check if current UTC time is within any kill zone."""
        from config import Config
        current_hour = datetime.now(timezone.utc).hour
        for zone_name, zone in Config.KILL_ZONES.items():
            start, end = zone['start'], zone['end']
            if start <= end:
                if start <= current_hour < end:
                    return True
            else:
                if current_hour >= start or current_hour < end:
                    return True
        return False

    @staticmethod
    def get_active_kill_zone() -> Optional[str]:
        """Get the name of the currently active kill zone, or None."""
        from config import Config
        current_hour = datetime.now(timezone.utc).hour
        for zone_name, zone in Config.KILL_ZONES.items():
            start, end = zone['start'], zone['end']
            if start <= end:
                if start <= current_hour < end:
                    return zone_name
            else:
                if current_hour >= start or current_hour < end:
                    return zone_name
        return None
