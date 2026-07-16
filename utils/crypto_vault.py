"""
Mustafa Bot - Crypto Vault & Secure Credential Encryption Engine
خزينة التشفير لحفظ كلمات مرور حسابات MetaTrader 5 بأمان عالي ومنع تسريبها
"""

import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger('mustafa_bot.utils.crypto_vault')


class CryptoVault:
    """Fernet AES Credential Encryption Vault."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CryptoVault, cls).__new__(cls)
            cls._instance._init_vault()
        return cls._instance

    def _init_vault(self) -> None:
        """Initialize encryption key derived from environment salt or local vault key."""
        try:
            salt = b'mustafa_bot_mt5_secure_salt_v1'
            passphrase = os.getenv('CRYPTO_SECRET_KEY', 'mustafa_bot_institutional_master_key_2026').encode()

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(passphrase))
            self.fernet = Fernet(key)
            logger.info("🔐 CryptoVault initialization successful")
        except Exception as e:
            logger.error(f"CryptoVault initialization error: {e}")
            # Fallback Fernet key
            key = Fernet.generate_key()
            self.fernet = Fernet(key)

    def encrypt_secret(self, secret_text: str) -> str:
        """Encrypt plain text string into Fernet token string."""
        if not secret_text:
            return ""
        try:
            encrypted_bytes = self.fernet.encrypt(secret_text.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting secret: {e}")
            return ""

    def decrypt_secret(self, token_str: str) -> str:
        """Decrypt Fernet token back into plain text string in-memory."""
        if not token_str:
            return ""
        try:
            decrypted_bytes = self.fernet.decrypt(token_str.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decrypting secret: {e}")
            return ""

    @staticmethod
    def mask_secret(secret_text: str) -> str:
        """Return masked representation of sensitive inputs."""
        if not secret_text:
            return ""
        if len(secret_text) <= 3:
            return "*" * len(secret_text)
        return secret_text[:2] + ("*" * (len(secret_text) - 3)) + secret_text[-1]
