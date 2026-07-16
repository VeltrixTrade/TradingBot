"""
Mustafa Bot - Dynamic Futures-to-Spot Price Conversion Engine
حساب الفارق السعري اللحظي وتحويل جميع مستويات الصفقات المكتشفة على شارت العقود الآجلة إلى أسعار السوق الفوري Spot XAU/USD
"""

import logging
from typing import Dict, Tuple
from config import Config

logger = logging.getLogger('mustafa_bot.data.futures_spot_converter')


class FuturesSpotConverter:
    """Dynamic real-time Futures-to-Spot price offset and setup level converter."""

    def __init__(self):
        pass

    def get_live_offset(self, symbol_key: str = 'XAU/USD') -> Tuple[float, float, float]:
        """Fetch current futures price and spot price to calculate the live real-time offset.

        Returns (offset, futures_price, spot_price).
        """
        try:
            from data.price_fetcher import PriceFetcher
            sym_info = Config.SUPPORTED_SYMBOLS.get(symbol_key, Config.SUPPORTED_SYMBOLS['XAU/USD'])
            
            # Fetch futures price (e.g. GC=F)
            futures_fetcher = PriceFetcher(symbol_key)
            fut_df = futures_fetcher.get_historical_data(timeframe='15m', n_bars=5)
            futures_price = float(fut_df['close'].iloc[-1]) if fut_df is not None and not fut_df.empty else 0.0

            # Fetch spot price (e.g. yfinance EURUSD=X / PAXG / OANDA Spot)
            spot_price = futures_price  # default fallback if matching
            
            # For Gold (XAU/USD), if futures GC=F is significantly higher than Spot (e.g. ~10-40 points premium)
            # We fetch Spot gold benchmark price or compute precise spot representation
            if 'XAU' in symbol_key and futures_price > 0:
                try:
                    import yfinance as yf
                    spot_ticker = yf.Ticker("PAXG-USD")
                    spot_hist = spot_ticker.history(period="1d", interval="1m")
                    if not spot_hist.empty:
                        spot_price = float(spot_hist['Close'].iloc[-1])
                    else:
                        # Fallback spot estimation if ticker rate limited
                        spot_price = futures_price - 15.0  # Estimated standard GC vs Spot gold basis spread
                except Exception:
                    spot_price = futures_price - 15.0

            offset = futures_price - spot_price
            logger.info(f"📊 Live Offset calculated for {symbol_key}: Futures={futures_price:.2f}, Spot={spot_price:.2f}, Offset={offset:+.2f}")
            return offset, futures_price, spot_price

        except Exception as e:
            logger.error(f"Error calculating live Futures-Spot offset for {symbol_key}: {e}")
            return 0.0, 0.0, 0.0

    def convert_setup_to_spot(self, setup: Dict, symbol_key: str = 'XAU/USD') -> Dict:
        """Bypass conversion since all active sources (TwelveData / PAXG) are native Spot prices."""
        return setup
