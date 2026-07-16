"""
Mustafa Bot - Quantitative Performance Analytics Engine
حساب إحصائيات الأداء المؤسساتية: نسبة النجاح، معامل الربحية، العائد المتوقع، الشارب، والتراجعات
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from database.db_manager import DatabaseManager

logger = logging.getLogger('mustafa_bot.analytics.performance')


class PerformanceAnalyticsEngine:
    """Quantitative performance calculation engine for trades database."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def calculate_performance_summary(self, symbol: Optional[str] = None) -> Dict:
        """Calculate complete quantitative performance metrics."""
        trades = self.db.get_all_trades(limit=500)
        
        if symbol:
            trades = [t for t in trades if t['symbol'] == symbol]

        closed_trades = [t for t in trades if t['status'] in ['TP1_HIT', 'TP2_HIT', 'TP3_HIT', 'SL_HIT', 'CLOSED']]
        total_closed = len(closed_trades)

        if total_closed == 0:
            return {
                'total_trades': len(trades),
                'closed_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'expectancy': 0.0,
                'sharpe_ratio': 0.0,
                'avg_rr': 0.0,
                'max_cons_wins': 0,
                'max_cons_losses': 0,
                'total_pnl': 0.0,
                'avg_mae': 0.0,
                'avg_mfe': 0.0,
                'formatted_summary': "📊 لا توجد صفقات مكتملة في قاعدة البيانات حتى الآن."
            }

        wins = 0
        losses = 0
        total_pnl = 0.0
        win_amounts = []
        loss_amounts = []
        rr_list = []
        mae_list = []
        mfe_list = []

        cons_wins = 0
        max_cons_wins = 0
        cons_losses = 0
        max_cons_losses = 0

        for t in reversed(closed_trades):  # Chronological order
            status = t['status']
            rr = t['risk_reward']
            pnl = t.get('pnl') or 0.0

            # Determine win or loss
            if status in ['TP1_HIT', 'TP2_HIT', 'TP3_HIT'] or pnl > 0:
                wins += 1
                cons_wins += 1
                max_cons_wins = max(max_cons_wins, cons_wins)
                cons_losses = 0
                
                win_val = pnl if pnl > 0 else rr * 100.0  # Estimated reward points
                win_amounts.append(win_val)
                total_pnl += win_val
            else:
                losses += 1
                cons_losses += 1
                max_cons_losses = max(max_cons_losses, cons_losses)
                cons_wins = 0

                loss_val = abs(pnl) if pnl < 0 else 100.0  # Estimated 1R risk points
                loss_amounts.append(loss_val)
                total_pnl -= loss_val

            rr_list.append(rr)
            if t.get('mae'): mae_list.append(t['mae'])
            if t.get('mfe'): mfe_list.append(t['mfe'])

        win_rate = (wins / total_closed) * 100.0
        avg_rr = sum(rr_list) / len(rr_list) if rr_list else 0.0
        
        sum_win_amt = sum(win_amounts)
        sum_loss_amt = sum(loss_amounts)
        profit_factor = (sum_win_amt / sum_loss_amt) if sum_loss_amt > 0 else (sum_win_amt if sum_win_amt > 0 else 1.0)

        avg_win = sum_win_amt / len(win_amounts) if win_amounts else 0.0
        avg_loss = sum_loss_amt / len(loss_amounts) if loss_amounts else 0.0
        
        win_prob = wins / total_closed
        loss_prob = losses / total_closed
        expectancy = (win_prob * avg_win) - (loss_prob * avg_loss)

        # Sharpe Ratio Estimation
        sharpe = 0.0
        all_returns = [w for w in win_amounts] + [-l for l in loss_amounts]
        if len(all_returns) > 1:
            mean_ret = sum(all_returns) / len(all_returns)
            var_ret = sum((r - mean_ret) ** 2 for r in all_returns) / (len(all_returns) - 1)
            std_ret = math.sqrt(var_ret)
            if std_ret > 0:
                sharpe = (mean_ret / std_ret) * math.sqrt(252)  # Annualized

        avg_mae = sum(mae_list) / len(mae_list) if mae_list else 0.0
        avg_mfe = sum(mfe_list) / len(mfe_list) if mfe_list else 0.0

        metrics = {
            'total_trades': len(trades),
            'closed_trades': total_closed,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'expectancy': round(expectancy, 2),
            'sharpe_ratio': round(sharpe, 2),
            'avg_rr': round(avg_rr, 2),
            'max_cons_wins': max_cons_wins,
            'max_cons_losses': max_cons_losses,
            'total_pnl': round(total_pnl, 2),
            'avg_mae': round(avg_mae, 2),
            'avg_mfe': round(avg_mfe, 2)
        }

        # Formatted Summary Text
        symbol_header = f"الرمز: {symbol}" if symbol else "كافة الرموز"
        metrics['formatted_summary'] = f"""📊 *تقرير الأداء الكمي والمؤسساتي* ({symbol_header}):
━━━━━━━━━━━━━━━━━━━━
📈 إجمالي الصفقات المكتملة: *{total_closed}*
✅ الصفقات الناجحة: *{wins}* ({win_rate:.1f}%)
❌ الصفقات الخاسرة: *{losses}*

⚖️ معامل الربحية (Profit Factor): *{profit_factor:.2f}*
🎯 العائد المتوقع لكل صفقة (Expectancy): *{expectancy:+.2f}$*
⚡ نسبة الشارب (Sharpe Ratio): *{sharpe:.2f}*
📏 متوسط نسبة المخاطرة للعائد (R:R): *1:{avg_rr:.1f}*

🔥 أطول سلسلة أرباح متتالية: *{max_cons_wins} صفقات*
❄️ أطول سلسلة خسائر متتالية: *{max_cons_losses} صفقات*
📉 متوسط الانحراف المعاكس (MAE): *{avg_mae:.2f} pips*
📈 متوسط أقصى ربح غير محقق (MFE): *{avg_mfe:.2f} pips*
━━━━━━━━━━━━━━━━━━━━
🤖 Mustafa Bot Institutional Analytics Engine"""

        return metrics
