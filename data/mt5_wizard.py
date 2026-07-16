"""
Mustafa Bot - MT5 Interactive Account Connection Wizard
معالج التخصيص التفاعلي لجمع بيانات اتصال حساب MetaTrader 5 خطوة بخطوة مع شاشة التأكيد والـ UI التفاعلي
"""

import logging
from typing import Dict, Optional
from utils.crypto_vault import CryptoVault

from typing import Dict, Optional, Tuple

logger = logging.getLogger('mustafa_bot.data.mt5_wizard')


class MT5SetupWizard:
    """Manages multi-step wizard state machine per user chat session."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5SetupWizard, cls).__new__(cls)
            cls._instance.user_wizard_data: Dict[int, Dict] = {}
            cls._instance.user_wizard_steps: Dict[int, str] = {}
        return cls._instance

    def start_wizard(self, chat_id: int) -> str:
        """Initialize wizard session for chat_id."""
        self.user_wizard_data[chat_id] = {
            'broker_name': '',
            'server': '',
            'login': 0,
            'password': '',
            'terminal_path': ''
        }
        self.user_wizard_steps[chat_id] = 'WAITING_BROKER'
        return 'WAITING_BROKER'

    def get_current_step(self, chat_id: int) -> str:
        """Retrieve active step for user session."""
        return self.user_wizard_steps.get(chat_id, 'IDLE')

    def record_input(self, chat_id: int, text_input: str) -> Tuple[str, str]:
        """Process incoming text input according to current step and advance wizard state."""
        current_step = self.get_current_step(chat_id)
        data = self.user_wizard_data.get(chat_id, {})

        if current_step == 'WAITING_BROKER':
            data['broker_name'] = text_input.strip()
            self.user_wizard_steps[chat_id] = 'WAITING_SERVER'
            return 'WAITING_SERVER', "🌐 *الخطوة [2/5]*: يرجى كتابة اسم خادم الحساب (*MT5 Server*) مثل:\n`ICMarketsSC-Live` أو `Exness-Real` أو `MetaQuotes-Demo`"

        elif current_step == 'WAITING_SERVER':
            data['server'] = text_input.strip()
            self.user_wizard_steps[chat_id] = 'WAITING_LOGIN'
            return 'WAITING_LOGIN', "🔢 *الخطوة [3/5]*: يرجى كتابة رقم الحساب (*Login / Account Number*) مثل:\n`50183921`"

        elif current_step == 'WAITING_LOGIN':
            clean_num = ''.join(c for c in text_input if c.isdigit())
            if not clean_num:
                return 'WAITING_LOGIN', "❌ *يرجى كتابة رقم حساب صحيح يتكون من أرقام فقط.*"
            data['login'] = int(clean_num)
            self.user_wizard_steps[chat_id] = 'WAITING_PASSWORD'
            return 'WAITING_PASSWORD', "🔑 *الخطوة [4/5]*: يرجى كتابة كلمة مرور الحساب (*Password*):\n\n🔒 *(سيتم تشفير كلمة المرور فورياً بترميز AES Fernet ولن تظهر في الشاشة أو السجلات)*"

        elif current_step == 'WAITING_PASSWORD':
            data['password'] = text_input.strip()
            self.user_wizard_steps[chat_id] = 'CONFIRMATION'
            return 'CONFIRMATION', self.get_summary_text(chat_id)

        return 'IDLE', "مرحبا بك في معالج الربط."

    def get_summary_text(self, chat_id: int) -> str:
        """Render markdown summary text for confirmation screen."""
        data = self.user_wizard_data.get(chat_id, {})
        masked_pwd = CryptoVault.mask_secret(data.get('password', ''))

        summary = (
            f"📋 *تأكيد بيانات اتصال حساب MetaTrader 5*:\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 اسم الوسيط (Broker): *{data.get('broker_name', 'N/A')}*\n"
            f"🌐 الخادم (Server): *{data.get('server', 'N/A')}*\n"
            f"🔢 رقم الحساب (Account): `{data.get('login', 0)}`\n"
            f"🔑 كلمة المرور (Password): `{masked_pwd}`\n"
            f"📡 الحالة: *في انتظار الاتصال والاختبار...*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"اضغط على زر (✅ اتصال بـ MT5) للبدء في تشفير البيانات واختبار الاتصال المباشر:"
        )
        return summary

    def reset_wizard(self, chat_id: int) -> None:
        """Clear wizard state for user session."""
        self.user_wizard_data.pop(chat_id, None)
        self.user_wizard_steps.pop(chat_id, None)
