"""
Mustafa Bot - Local MT5 Bridge Service Launcher
مشغّل الجسر المحلي لربط منصة MetaTrader 5 وسيرفر Uvicorn بـ REST API
"""

import sys
import os
import uvicorn

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("🌐 MUSTAFA BOT - LOCAL MT5 FASTAPI BRIDGE SERVICE")
    print("=" * 60)
    print("⚡ Protocol : HTTP REST API + WebSockets")
    print("🔐 Security : Bearer Token Key Authentication")
    print("📊 Engine   : MetaTrader 5 Native Terminal Interface")
    print("=" * 60)
    print("🚀 Starting FastAPI Uvicorn Server on http://127.0.0.1:8000 ...")
    print("📱 Documentation available at: http://127.0.0.1:8000/docs")
    print("=" * 60)

    uvicorn.run(
        "mt5_bridge_server.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == '__main__':
    main()
