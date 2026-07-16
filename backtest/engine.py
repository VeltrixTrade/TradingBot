"""
Mustafa Bot - Historical Backtesting Engine
إجراء اختبار رادعي تاريخي لاستراتيجية SMC + ICT وحساب معدل الفوز، التراجع، ومنحنى الأرباح
"""

import math
import logging
from typing import Dict, List, Optional
import pandas as pd
from data.price_fetcher import PriceFetcher
from analysis.gold_engine import GoldMarketAnalysisEngine
from config import Config

logger = logging.getLogger('mustafa_bot.backtest.engine')


class HistoricalBacktestEngine:
    """Simulates SMC/ICT multi-timeframe strategy execution on historical OHLCV data."""

    def __init__(self):
        self.gold_engine = GoldMarketAnalysisEngine()

    def run_backtest(self, symbol_key: str = 'XAU/USD', signal_type: str = 'SCALP', n_bars: int = 500, profile: str = 'CONSERVATIVE') -> Dict:
        """Run strategy backtest simulation on historical market data."""
        logger.info(f"🧪 Running historical backtest for {symbol_key} ({signal_type}, Profile: {profile}, Bars: {n_bars})...")
        
        fetcher = PriceFetcher(symbol_key)
        tf_list = ['1mo', '1w', '1d', '4h', '1h', '30m', '15m', '5m']
        data = fetcher.get_multi_timeframe_data(tf_list)

        if not data or '15m' not in data:
            return {
                'status': 'ERROR',
                'error': 'Incomplete historical candle data available for backtesting.',
                'formatted_report': f"❌ تعذر جلب البيانات التاريخية الكافية لـ {symbol_key} لإجراء الاختبار."
            }

        exec_tf = '15m' if signal_type == 'SCALP' else '1h'
        df = data[exec_tf]
        
        if len(df) < 50:
            return {
                'status': 'ERROR',
                'error': 'Insufficient historical candles slice.',
                'formatted_report': f"❌ عينة الشموع التاريخية غير كافية لـ {symbol_key}."
            }

        # Profile score threshold
        profile_config = Config.TRADING_PROFILES.get(profile, Config.TRADING_PROFILES['CONSERVATIVE'])
        threshold_score = profile_config['min_score']

        setups_found = 0
        wins = 0
        losses = 0
        total_r = 0.0
        equity_curve = [100.0]  # Starting 100% equity
        peak_equity = 100.0
        max_drawdown = 0.0
        trades_log = []

        # Step through historical windows
        step_size = 5
        window_size = min(300, len(df) - 20)

        for i in range(window_size, len(df) - 10, step_size):
            # Create sliced historical dataframes dictionary
            sub_dfs = {}
            for tf_k, tf_df in data.items():
                if len(tf_df) > i:
                    sub_dfs[tf_k] = tf_df.iloc[:i]
                else:
                    sub_dfs[tf_k] = tf_df

            # Run analysis engine
            report = self.gold_engine.analyze_market(sub_dfs, signal_type, symbol_key=symbol_key)
            setups = report.get('setups', [])

            for s in setups:
                score = s['score']
                if score < threshold_score:
                    continue

                setups_found += 1
                direction = s['direction']
                entry = s['entry']
                sl = s['stop_loss']
                tp1 = s['tp1']
                tp2 = s['tp2']

                # Simulate future price movement using subsequent candles
                future_df = df.iloc[i:i + 15]
                trade_result = 'CLOSED'
                pnl_r = 0.0

                for _, candle in future_df.iterrows():
                    high = candle['high']
                    low = candle['low']

                    if direction == 'BUY':
                        if high >= tp2:
                            wins += 1
                            trade_result = 'WIN_TP2'
                            pnl_r = s['risk_reward']
                            break
                        elif high >= tp1:
                            wins += 1
                            trade_result = 'WIN_TP1'
                            pnl_r = 1.0
                            break
                        elif low <= sl:
                            losses += 1
                            trade_result = 'LOSS_SL'
                            pnl_r = -1.0
                            break
                    else:  # SELL
                        if low <= tp2:
                            wins += 1
                            trade_result = 'WIN_TP2'
                            pnl_r = s['risk_reward']
                            break
                        elif low <= tp1:
                            wins += 1
                            trade_result = 'WIN_TP1'
                            pnl_r = 1.0
                            break
                        elif high >= sl:
                            losses += 1
                            trade_result = 'LOSS_SL'
                            pnl_r = -1.0
                            break

                if trade_result != 'CLOSED':
                    total_r += pnl_r
                    current_eq = equity_curve[-1] + (pnl_r * 2.0)  # 2% risk per trade
                    equity_curve.append(current_eq)
                    peak_equity = max(peak_equity, current_eq)
                    dd = ((peak_equity - current_eq) / peak_equity) * 100.0
                    max_drawdown = max(max_drawdown, dd)

                    trades_log.append({
                        'step': i,
                        'direction': direction,
                        'score': score,
                        'result': trade_result,
                        'pnl_r': pnl_r
                    })

        total_simulated = wins + losses
        win_rate = (wins / total_simulated * 100.0) if total_simulated > 0 else 0.0
        profit_factor = (wins * 1.5 / max(1, losses)) if losses > 0 else (wins * 1.5 if wins > 0 else 1.0)
        expectancy = ((win_rate / 100.0) * 1.5) - (((100.0 - win_rate) / 100.0) * 1.0)

        # Performance assessment text
        stability = "HIGH 🟢" if win_rate >= 65 and max_drawdown <= 10 else "MODERATE 🟡" if win_rate >= 50 else "NEEDS OPTIMIZATION 🔴"

        formatted_report = f"""🧪 *نتائج الاختبار التاريخي (Backtest Report)*
━━━━━━━━━━━━━━━━━━━━
🌐 الرمز: *{symbol_key}* | النمط: *{profile}*
📊 عدد إشارات الفحص: *{setups_found}*
✅ الصفقات المحاكاة: *{total_simulated}*
🏆 معدل النجاح (Win Rate): *{win_rate:.1f}%*
⚖️ معامل الربحية (Profit Factor): *{profit_factor:.2f}*
🎯 الـ Expectancy لكل صفقة: *{expectancy:+.2f}R*

📉 أقصى انخفاض لمحفظة الحساب (Max Drawdown): *{max_drawdown:.1f}%*
📈 إجمالي صافي الـ R المحقق: *{total_r:+.1f}R*
🛡️ تقييم ثبات الاستراتيجية: *{stability}*
━━━━━━━━━━━━━━━━━━━━
💡 *توصية المحرك الكَمّي*:
  {'النتائجممتازة ومطابقة للمواصفات المؤسساتية ✅' if win_rate >= 60 else 'يُفضل استخدام النمط المحافظ (Conservative) لرفع نسبة النجاح وتقليل التذبذب.'}
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot Backtesting Engine v2.5"""

        return {
            'status': 'SUCCESS',
            'symbol': symbol_key,
            'setups_found': setups_found,
            'total_simulated': total_simulated,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'expectancy': round(expectancy, 2),
            'max_drawdown': round(max_drawdown, 1),
            'total_r': round(total_r, 1),
            'stability': stability,
            'formatted_report': formatted_report
        }
