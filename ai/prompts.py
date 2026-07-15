"""
Mustafa Bot - AI Prompts
قوالب البرومبتات المتخصصة لتحليل الذهب
"""


class Prompts:
    """Expert prompts for gold trading analysis."""

    SYSTEM_PROMPT = """You are an elite Gold (XAU/USD) trading expert with over 20 years of institutional trading experience. You specialize in Smart Money Concepts (SMC) and Inner Circle Trader (ICT) methodology.

Your expertise includes:
- Identifying institutional order flow and smart money footprints
- Break of Structure (BOS) and Change of Character (CHoCH) analysis
- Order Block identification, validation, and entry timing
- Fair Value Gap (FVG) trading and imbalance zones
- Liquidity sweep detection and stop hunt recognition
- Kill Zone timing (London 08:00-12:00 UTC, New York 13:00-17:00 UTC, Asian 00:00-03:00 UTC)
- Premium/Discount zone analysis for optimal entries
- Multi-timeframe confluence analysis (HTF bias → LTF entry)
- Risk management with minimum 1:2 Risk-to-Reward ratio

You analyze gold with the precision of a 20-year veteran trader. You understand that:
- Price is attracted to liquidity (equal highs/lows, stop clusters)
- Institutions leave footprints via order blocks and imbalances
- Market structure shifts signal potential reversals
- Higher timeframe bias should guide lower timeframe entries
- Kill zones offer the highest probability setups

You MUST respond ONLY in valid JSON format with this exact structure:
{
    "direction": "BUY" or "SELL" or "NEUTRAL",
    "confidence": 0-100,
    "entry": price_level,
    "stop_loss": price_level,
    "take_profit_1": price_level,
    "take_profit_2": price_level,
    "take_profit_3": price_level,
    "reasoning": "detailed analysis in Arabic",
    "prediction": "price prediction for next 4-24 hours in Arabic",
    "reversal_zones": [price1, price2, price3],
    "risk_level": "LOW" or "MEDIUM" or "HIGH",
    "setup_type": "e.g., Bullish OB + FVG Confluence"
}

IMPORTANT: Output ONLY the JSON object, no markdown, no explanation outside JSON."""

    @staticmethod
    def build_analysis_prompt(market_data: dict, smc_analysis: dict) -> str:
        """Build comprehensive analysis prompt with market data."""
        current_price = smc_analysis.get('current_price', 0)
        ms = smc_analysis.get('market_structure', {})
        obs = smc_analysis.get('order_blocks', [])
        fvgs = smc_analysis.get('fair_value_gaps', [])
        liq = smc_analysis.get('liquidity', {})
        ind = smc_analysis.get('indicators', {})

        # Format order blocks
        ob_text = "None detected"
        if obs:
            ob_lines = []
            for ob in obs[:5]:
                ob_lines.append(
                    f"  - {ob['type']} OB: {ob['bottom']:.2f} - {ob['top']:.2f} "
                    f"(Strength: {ob['strength']}/10, Mitigated: {ob.get('mitigated', False)})"
                )
            ob_text = "\n".join(ob_lines)

        # Format FVGs
        fvg_text = "None detected"
        if fvgs:
            fvg_lines = []
            for fvg in fvgs[:5]:
                fvg_lines.append(
                    f"  - {fvg['type']} FVG: {fvg['bottom']:.2f} - {fvg['top']:.2f} "
                    f"(Fill: {fvg['fill_percentage']:.1f}%)"
                )
            fvg_text = "\n".join(fvg_lines)

        # Format liquidity
        buy_liq = liq.get('buy_side', [])
        sell_liq = liq.get('sell_side', [])
        sweeps = liq.get('sweeps', [])
        liq_text = f"Buy-side pools: {len(buy_liq)}, Sell-side pools: {len(sell_liq)}, Recent sweeps: {len(sweeps)}"

        # Format key levels
        key_levels = smc_analysis.get('key_levels', [])
        levels_text = ', '.join([f'{l:.2f}' for l in key_levels[:10]]) if key_levels else "None"

        prompt = f"""Analyze the following XAUUSD (Gold) market data and provide a trading signal.

═══ CURRENT STATE ═══
• Current Price: {current_price:.2f}
• Timeframe: {smc_analysis.get('timeframe', 'M15')}
• Overall Bias: {smc_analysis.get('overall_bias', 'NEUTRAL')}
• Premium/Discount: {smc_analysis.get('premium_discount', 'EQUILIBRIUM')}
• Setup Quality Score: {smc_analysis.get('score', 0)}/100

═══ MARKET STRUCTURE ═══
• Trend: {ms.get('trend', 'NEUTRAL')}
• Structure Strength: {ms.get('structure_strength', 0)}%
• Last Swing High: {ms.get('last_swing_high', 'N/A')}
• Last Swing Low: {ms.get('last_swing_low', 'N/A')}
• Recent BOS: {len(ms.get('bos_list', []))} events
• Recent CHoCH: {len(ms.get('choch_list', []))} events

═══ ORDER BLOCKS ═══
{ob_text}

═══ FAIR VALUE GAPS ═══
{fvg_text}

═══ LIQUIDITY ═══
{liq_text}

═══ TECHNICAL INDICATORS ═══
• RSI(14): {ind.get('rsi', 50):.1f}
• ATR(14): {ind.get('atr', 0):.2f}
• EMA 20: {ind.get('ema_20', 0):.2f}
• EMA 50: {ind.get('ema_50', 0):.2f}
• EMA 200: {ind.get('ema_200', 0):.2f}
• Volatility: {ind.get('volatility', 'MEDIUM')}

═══ KEY LEVELS ═══
{levels_text}

Based on this SMC/ICT analysis, provide your trading signal in JSON format.
Consider all confluences and provide precise entry, stop loss, and 3 take profit levels.
Your reasoning MUST be in Arabic."""

        return prompt

    @staticmethod
    def build_scalp_prompt(market_data: dict, smc_analysis: dict) -> str:
        """Build prompt for scalp trading (M1-M15)."""
        base = Prompts.build_analysis_prompt(market_data, smc_analysis)
        scalp_context = """

═══ SCALP TRADING CONTEXT ═══
This is a SCALP trade setup (M1-M15 timeframes).
Requirements:
- Entry should be precise, close to the current price
- Stop Loss: 3-8 USD from entry (tight)
- Take Profit 1: 1.5-2x the risk
- Take Profit 2: 2.5-3x the risk
- Take Profit 3: 4-5x the risk
- Focus on momentum and quick execution
- Prioritize setups within active Kill Zones
- Higher confidence required (>75%)
"""
        return base + scalp_context

    @staticmethod
    def build_swing_prompt(market_data: dict, smc_analysis: dict) -> str:
        """Build prompt for swing trading (H1-D1)."""
        base = Prompts.build_analysis_prompt(market_data, smc_analysis)
        swing_context = """

═══ SWING TRADING CONTEXT ═══
This is a SWING trade setup (H1-D1 timeframes).
Requirements:
- Entry can be at key levels, not necessarily at current price
- Stop Loss: 10-25 USD from entry (wider)
- Take Profit 1: 2-3x the risk
- Take Profit 2: 3-5x the risk
- Take Profit 3: 5-8x the risk
- Focus on the bigger picture and trend following
- Consider daily and weekly key levels
- Patience is key - wait for optimal entry
"""
        return base + swing_context

    @staticmethod
    def build_prediction_prompt(market_data: dict, smc_analysis: dict) -> str:
        """Build prompt for price prediction."""
        current_price = smc_analysis.get('current_price', 0)
        ms = smc_analysis.get('market_structure', {})
        key_levels = smc_analysis.get('key_levels', [])

        levels_text = ', '.join([f'{l:.2f}' for l in key_levels[:10]]) if key_levels else "None"

        prompt = f"""Based on the following XAUUSD (Gold) data, provide a price prediction.

Current Price: {current_price:.2f}
Trend: {ms.get('trend', 'NEUTRAL')}
Last Swing High: {ms.get('last_swing_high', 'N/A')}
Last Swing Low: {ms.get('last_swing_low', 'N/A')}
Key Levels: {levels_text}

Provide your response in this JSON format:
{{
    "direction": "BUY" or "SELL" or "NEUTRAL",
    "confidence": 0-100,
    "entry": {current_price},
    "stop_loss": 0,
    "take_profit_1": 0,
    "take_profit_2": 0,
    "take_profit_3": 0,
    "reasoning": "Price prediction analysis in Arabic",
    "prediction": "Detailed 4h/12h/24h price prediction in Arabic including: expected range, potential scenarios (bullish/bearish), and key levels to watch",
    "reversal_zones": [zone1, zone2, zone3, zone4, zone5],
    "risk_level": "LOW" or "MEDIUM" or "HIGH",
    "setup_type": "Price Prediction"
}}

Focus on:
1. Next 4 hours price range prediction
2. Next 12 hours price range prediction
3. Next 24 hours price range prediction
4. Key reversal zones (at least 5 levels)
5. Most likely scenario with probability

All text in Arabic."""

        return prompt
