"""
Mustafa Bot - Persistent Message Manager
إدارة الرسالة الموحدة وتحديثها بشكل ديناميكي لتفادي السبام وحذف رسائل المستخدم تلقائياً
"""

import logging
from telegram.error import TelegramError

logger = logging.getLogger('mustafa_bot.bot.message_manager')


class MessageManager:
    """Manages a single persistent interface message per user and keeps the chat clean."""

    def __init__(self):
        self.messages = {}  # maps chat_id -> message_id

    async def send_or_edit(self, bot, chat_id: int, text: str, reply_markup=None, parse_mode: str = "Markdown") -> None:
        """Edit the active persistent message, or send a new one if not found or expired."""
        message_id = self.messages.get(chat_id)
        
        if message_id:
            try:
                # Attempt to edit the persistent message
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                return
            except TelegramError as e:
                # If content is exactly the same, ignore
                if "Message is not modified" in str(e):
                    return
                logger.warning(f"Failed to edit message {message_id} for chat {chat_id}: {e}. Sending new message.")

        # Send a new message if edit fails or no message exists
        try:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            self.messages[chat_id] = msg.message_id
        except Exception as ex:
            logger.error(f"Failed to send message to chat {chat_id}: {ex}")

    async def delete_user_message(self, bot, chat_id: int, message_id: int) -> None:
        """Delete user's incoming message to keep the chat clean and professional."""
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.debug(f"Failed to delete user message {message_id} in chat {chat_id}: {e}")
