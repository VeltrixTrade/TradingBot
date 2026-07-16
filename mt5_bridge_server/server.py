"""
Mustafa Bot - Professional FastAPI MT5 Bridge Server
سيرفر الـ REST API والتكات الفورية لخدمة البوت السحابي ومربوط مباشرة بحساب تداولك المحلي
"""

import asyncio
import logging
from typing import List, Dict, Optional
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from mt5_bridge_server.bridge_manager import NativeMT5BridgeManager
from mt5_bridge_server.security import verify_api_key

logger = logging.getLogger('mt5_bridge.server')

app = FastAPI(
    title="Mustafa Bot - MT5 Bridge API",
    description="High-Speed Low-Latency Local MetaTrader 5 REST & WebSocket Bridge Server",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bridge_mgr = NativeMT5BridgeManager()


@app.on_event("startup")
async def startup_event():
    """Connect to local MT5 terminal on server startup."""
    logger.info("🚀 Launching local MT5 Bridge API Server...")
    bridge_mgr.connect()


# Active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()


# ── REST API Endpoints ──

@app.get("/health")
async def get_health():
    """Check bridge health, MT5 connection status, and ping latency."""
    return bridge_mgr.get_health_status()


@app.get("/symbols", dependencies=[Depends(verify_api_key)])
async def get_symbols():
    """Return all discovered broker symbols."""
    syms = bridge_mgr.discover_symbols()
    return {"symbols": syms}


@app.get("/symbol/{symbol}", dependencies=[Depends(verify_api_key)])
async def get_symbol_info(symbol: str):
    """Return symbol specifications and current market state."""
    clean_sym = symbol.replace('%2F', '/').replace('-', '/')
    info = bridge_mgr.get_symbol_info(clean_sym)
    if not info:
        raise HTTPException(status_code=404, detail=f"Symbol {clean_sym} not found on broker terminal")
    return info


@app.get("/price/{symbol}", dependencies=[Depends(verify_api_key)])
async def get_price(symbol: str):
    """Return real-time Bid, Ask, Spread (pips), Last Price, and Timestamp."""
    clean_sym = symbol.replace('%2F', '/').replace('-', '/')
    info = bridge_mgr.get_symbol_info(clean_sym)
    if not info:
        raise HTTPException(status_code=404, detail=f"Price unavailable for {clean_sym}")
    return {
        'symbol': clean_sym,
        'bid': info['bid'],
        'ask': info['ask'],
        'spread_pips': info['spread_pips'],
        'last': info['last'],
        'timestamp': info['timestamp']
    }


@app.get("/candles/{symbol}/{timeframe}", dependencies=[Depends(verify_api_key)])
async def get_candles(symbol: str, timeframe: str, limit: int = Query(default=500, le=2000)):
    """Return historical OHLCV candles."""
    clean_sym = symbol.replace('%2F', '/').replace('-', '/')
    candles = bridge_mgr.get_candles(clean_sym, timeframe, limit)
    if candles is None:
        raise HTTPException(status_code=404, detail=f"Failed to fetch candles for {clean_sym} ({timeframe})")
    return {
        'symbol': clean_sym,
        'timeframe': timeframe,
        'count': len(candles),
        'candles': candles
    }


@app.get("/account", dependencies=[Depends(verify_api_key)])
async def get_account():
    """Return MT5 account details."""
    acc = bridge_mgr.get_account_info()
    if not acc:
        raise HTTPException(status_code=503, detail="MT5 account information unavailable")
    return acc


@app.get("/positions", dependencies=[Depends(verify_api_key)])
async def get_positions():
    """Return open active positions."""
    return {"positions": bridge_mgr.get_positions()}


@app.get("/orders", dependencies=[Depends(verify_api_key)])
async def get_orders():
    """Return pending active orders."""
    return {"orders": bridge_mgr.get_orders()}


# ── WebSocket Stream ──

@app.websocket("/ws/ticks")
async def websocket_ticks(websocket: WebSocket, symbol: str = 'XAU/USD'):
    """Stream live real-time price updates for scalp analysis."""
    await ws_manager.connect(websocket)
    clean_sym = symbol.replace('%2F', '/').replace('-', '/')
    try:
        while True:
            info = bridge_mgr.get_symbol_info(clean_sym)
            if info:
                await websocket.send_json(info)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
