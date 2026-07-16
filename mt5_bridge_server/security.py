"""
Mustafa Bot - MT5 Bridge Server Security Module
التحقق والأمان باستخدام مفتاح API Key وتشفير الـ Bearer Token لمنع الوصول غير المصرح
"""

import os
import logging
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger('mt5_bridge.security')

security_bearer = HTTPBearer(auto_error=False)

API_KEY = os.getenv('BRIDGE_API_KEY', 'mustafa_bot_mt5_bridge_secret_key_2026')


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security_bearer)) -> str:
    """Verify incoming Bearer token API key."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer Header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    provided_key = credentials.credentials
    if provided_key != API_KEY:
        logger.warning(f"Unauthorized access attempt with key: {provided_key[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or Unauthorized API Key",
        )

    return provided_key
