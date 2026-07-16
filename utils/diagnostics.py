"""
Mustafa Bot - Centralized Diagnostics & Structured Logging
يوفر تسجيل مركزي مهيكل للأحداث والمخاطر وأخطاء المزودين مع إجراءات التعافي التلقائي
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional

logger = logging.getLogger('mustafa_bot.utils.diagnostics')


@dataclass
class DiagnosticEvent:
    """Structured diagnostic event model."""
    timestamp: str
    module: str
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    description: str
    details: Optional[Dict] = None
    recovery_action: Optional[str] = None


class DiagnosticsManager:
    """Centralized diagnostic and event tracking engine."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DiagnosticsManager, cls).__new__(cls)
            cls._instance.events: List[DiagnosticEvent] = []
            cls._instance.max_events = 200
            cls._instance.data_feed_status = "HEALTHY"
            cls._instance.api_errors_count = 0
            cls._instance.last_analysis_time: Optional[str] = None
        return cls._instance

    def log_event(
        self,
        module: str,
        severity: str,
        description: str,
        details: Optional[Dict] = None,
        recovery_action: Optional[str] = None
    ) -> DiagnosticEvent:
        """Log a structured diagnostic event."""
        now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        event = DiagnosticEvent(
            timestamp=now_str,
            module=module,
            severity=severity.upper(),
            description=description,
            details=details or {},
            recovery_action=recovery_action
        )

        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events.pop(0)

        # Log formatted text
        log_msg = f"[{event.severity}] [{module}] {description}"
        if recovery_action:
            log_msg += f" | Action: {recovery_action}"

        if event.severity in ['ERROR', 'CRITICAL']:
            logger.error(log_msg)
            self.api_errors_count += 1
        elif event.severity == 'WARNING':
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return event

    def update_data_feed_status(self, status: str) -> None:
        """Update data feed state (e.g. HEALTHY, DEGRADED, DOWN)."""
        self.data_feed_status = status

    def update_last_analysis_time(self) -> None:
        """Mark last analysis timestamp."""
        self.last_analysis_time = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')

    def get_recent_events(self, limit: int = 15, severity: Optional[str] = None) -> List[DiagnosticEvent]:
        """Retrieve latest diagnostic events."""
        filtered = self.events
        if severity:
            filtered = [e for e in filtered if e.severity == severity.upper()]
        return filtered[-limit:]

    def get_system_health_report(self) -> str:
        """Generate structured text summary of overall system status."""
        recent_errs = [e for e in self.events if e.severity in ['ERROR', 'CRITICAL']]
        last_err_text = recent_errs[-1].description if recent_errs else "No recent errors"

        report = f"""🛠️ *تقرير تشخيص النظام وحالة الخوادم*:
━━━━━━━━━━━━━━━━━━━━
📡 حالة جلب البيانات: *{self.data_feed_status}*
🧠 أخطاء الـ API المسجلة: *{self.api_errors_count}*
⏰ آخر عملية تحليل: *{self.last_analysis_time or 'جاري التشغيل...'}*
🚨 آخر تنبيه لنظام التعافي: *{last_err_text}*
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot Institutional Engine v2.5"""
        return report
