"""
Mustafa Bot - SQLite Database Persistence Engine
إدارة تتبع الصفقات، التحولات بين المراحل، وسجل الإحصائيات التاريخية
"""

import os
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

logger = logging.getLogger('mustafa_bot.database.db_manager')


class DatabaseManager:
    """SQLite Database manager for trade lifecycle persistence and quantitative analytics."""

    _instance = None

    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mustafa_bot.db')
            cls._instance._init_db()
        return cls._instance

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema tables if not exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Trades Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    entry REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    tp1 REAL NOT NULL,
                    tp2 REAL NOT NULL,
                    tp3 REAL NOT NULL,
                    confidence_score INTEGER NOT NULL,
                    risk_reward REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    closed_at TEXT,
                    exit_price REAL,
                    duration_seconds INTEGER,
                    pnl REAL,
                    result TEXT,
                    close_reason TEXT,
                    mae REAL DEFAULT 0.0,
                    mfe REAL DEFAULT 0.0,
                    analysis_report TEXT
                );
                """)

                # State Transitions Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    trigger_price REAL,
                    timestamp TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY(trade_id) REFERENCES trades(id)
                );
                """)

                # MT5 Encrypted Credentials Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS mt5_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER UNIQUE NOT NULL,
                    broker_name TEXT,
                    server TEXT NOT NULL,
                    login INTEGER NOT NULL,
                    encrypted_password TEXT NOT NULL,
                    terminal_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """)

                # Users Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """)

                # Bot Settings Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """)

                # Bot Templates Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_templates (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """)

                # Admin Action Logs Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT
                );
                """)

                # Rejected Signals Audit Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS rejected_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    strategy TEXT DEFAULT 'SMC/ICT',
                    direction TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    score_components TEXT DEFAULT '{}',
                    risk_reward REAL NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT
                );
                """)

                # Strategy Performance Evaluations Table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    accepted INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    risk_reward REAL NOT NULL
                );
                """)

                conn.commit()
                logger.info("💾 Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)

    def insert_trade(self, trade_data: Dict) -> bool:
        """Insert a new trade record into the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Check for order_type column compatibility
                cursor.execute("PRAGMA table_info(trades)")
                cols = [c['name'] for c in cursor.fetchall()]

                if 'order_type' in cols and 'expiration_time' in cols:
                    cursor.execute("""
                    INSERT INTO trades (
                        id, symbol, direction, order_type, timeframe, entry, stop_loss,
                        tp1, tp2, tp3, confidence_score, risk_reward, status, expiration_time,
                        created_at, mae, mfe, analysis_report
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade_data['id'],
                        trade_data['symbol'],
                        trade_data['direction'],
                        trade_data.get('order_type', 'MARKET_BUY'),
                        trade_data['timeframe'],
                        trade_data['entry'],
                        trade_data['stop_loss'],
                        trade_data['tp1'],
                        trade_data['tp2'],
                        trade_data['tp3'],
                        trade_data['confidence_score'],
                        trade_data['risk_reward'],
                        trade_data.get('status', 'PENDING'),
                        trade_data.get('expiration_time', ''),
                        trade_data.get('created_at', now_str),
                        0.0, 0.0,
                        trade_data.get('analysis_report', '')
                    ))
                else:
                    cursor.execute("""
                    INSERT INTO trades (
                        id, symbol, direction, timeframe, entry, stop_loss,
                        tp1, tp2, tp3, confidence_score, risk_reward, status,
                        created_at, mae, mfe, analysis_report
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade_data['id'],
                        trade_data['symbol'],
                        trade_data['direction'],
                        trade_data['timeframe'],
                        trade_data['entry'],
                        trade_data['stop_loss'],
                        trade_data['tp1'],
                        trade_data['tp2'],
                        trade_data['tp3'],
                        trade_data['confidence_score'],
                        trade_data['risk_reward'],
                        trade_data.get('status', 'PENDING'),
                        trade_data.get('created_at', now_str),
                        0.0, 0.0,
                        trade_data.get('analysis_report', '')
                    ))

                # Log initial state transition
                cursor.execute("""
                INSERT INTO state_transitions (trade_id, from_status, to_status, trigger_price, timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    trade_data['id'],
                    'NONE',
                    trade_data.get('status', 'PENDING'),
                    trade_data['entry'],
                    now_str,
                    'Signal Created & Initialized'
                ))

                conn.commit()
                logger.info(f"💾 Trade {trade_data['id']} ({trade_data['symbol']}) inserted into DB")
                return True
        except Exception as e:
            logger.error(f"Error inserting trade into DB: {e}")
            return False

    def update_trade_status(self, trade_id: str, new_status: str, trigger_price: Optional[float] = None, notes: str = "") -> bool:
        """Update active trade status and record transition log."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Fetch existing trade
                cursor.execute("SELECT status, entry FROM trades WHERE id = ?", (trade_id,))
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Trade {trade_id} not found in database")
                    return False

                current_status = row['status']
                if current_status == new_status:
                    return True

                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Check terminal statuses
                is_closed = new_status in ['TP3_HIT', 'SL_HIT', 'CLOSED', 'CANCELLED']
                exit_price = trigger_price if is_closed else None
                close_reason = notes if is_closed else None

                update_sql = "UPDATE trades SET status = ?"
                params = [new_status]

                if is_closed:
                    update_sql += ", closed_at = ?, exit_price = ?, close_reason = ?"
                    params.extend([now_str, exit_price, close_reason])

                update_sql += " WHERE id = ?"
                params.append(trade_id)

                cursor.execute(update_sql, params)

                # Record transition
                cursor.execute("""
                INSERT INTO state_transitions (trade_id, from_status, to_status, trigger_price, timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (trade_id, current_status, new_status, trigger_price, now_str, notes))

                conn.commit()
                logger.info(f"🔄 Trade {trade_id} status updated: {current_status} -> {new_status}")
                return True
        except Exception as e:
            logger.error(f"Error updating trade status in DB: {e}")
            return False

    def update_trade_excursion(self, trade_id: str, mae: float, mfe: float) -> None:
        """Update Maximum Adverse Excursion (MAE) and Maximum Favorable Excursion (MFE)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE trades SET mae = max(mae, ?), mfe = max(mfe, ?) WHERE id = ?", (mae, mfe, trade_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating trade excursion in DB: {e}")

    def get_active_trades(self) -> List[Dict]:
        """Fetch all trades currently in active states (ACTIVE, PENDING, TP1_HIT, TP2_HIT)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM trades 
                WHERE status IN ('ACTIVE', 'PENDING', 'WAITING_ENTRY', 'TP1_HIT', 'TP2_HIT')
                ORDER BY created_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching active trades: {e}")
            return []

    def get_active_pending_orders(self) -> List[Dict]:
        """Fetch all trades currently in PENDING state awaiting activation."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM trades 
                WHERE status IN ('PENDING', 'WAITING_ENTRY')
                ORDER BY created_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching pending orders: {e}")
            return []

    def get_all_trades(self, limit: int = 50) -> List[Dict]:
        """Fetch historical trade records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []

    # ── MT5 Credentials Management ──

    def save_mt5_account(self, chat_id: int, broker_name: str, server: str, login: int, encrypted_password: str, terminal_path: str = "") -> bool:
        """Insert or update encrypted MT5 account credentials for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                cursor.execute("""
                INSERT INTO mt5_credentials (chat_id, broker_name, server, login, encrypted_password, terminal_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    broker_name = excluded.broker_name,
                    server = excluded.server,
                    login = excluded.login,
                    encrypted_password = excluded.encrypted_password,
                    terminal_path = excluded.terminal_path,
                    updated_at = excluded.updated_at
                """, (chat_id, broker_name, server, login, encrypted_password, terminal_path, now_str, now_str))
                conn.commit()
                logger.info(f"🔐 Encrypted MT5 credentials stored for chat_id={chat_id} (Login: {login})")
                return True
        except Exception as e:
            logger.error(f"Error saving MT5 credentials in DB: {e}")
            return False

    def get_mt5_account(self, chat_id: int) -> Optional[Dict]:
        """Fetch encrypted MT5 credentials for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM mt5_credentials WHERE chat_id = ?", (chat_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching MT5 credentials from DB: {e}")
            return None

    def delete_mt5_account(self, chat_id: int) -> bool:
        """Remove MT5 account credentials for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM mt5_credentials WHERE chat_id = ?", (chat_id,))
                conn.commit()
                logger.info(f"🗑️ MT5 credentials removed for chat_id={chat_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting MT5 credentials from DB: {e}")
            return False

    # ── User Tracking Management ──

    def register_user(self, chat_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Register a user in the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                cursor.execute("""
                INSERT INTO users (chat_id, username, first_name, last_name, status, created_at)
                VALUES (?, ?, ?, ?, 'active', ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name
                """, (chat_id, username, first_name, last_name, now_str))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False

    def get_users_count(self) -> int:
        """Get total user count."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0

    def get_today_users_count(self) -> int:
        """Get count of users registered today."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                today_prefix = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                cursor.execute("SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (f"{today_prefix}%",))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error counting today's users: {e}")
            return 0

    def get_active_users(self) -> List[Dict]:
        """Fetch all active users."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE status = 'active'")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching active users: {e}")
            return []

    def get_all_users(self) -> List[Dict]:
        """Fetch all users."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            return []

    def update_user_status(self, chat_id: int, status: str) -> bool:
        """Update a user status (active/blocked)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET status = ? WHERE chat_id = ?", (status, chat_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
            return False

    # ── Bot Settings Management ──

    def save_setting(self, key: str, value: str) -> bool:
        """Save a setting value."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO bot_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """, (key, value))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving setting {key}: {e}")
            return False

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a setting value."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row['value'] if row else default
        except Exception as e:
            logger.error(f"Error fetching setting {key}: {e}")
            return default

    # ── Bot Templates Management ──

    def save_template(self, key: str, value: str) -> bool:
        """Save a message template."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO bot_templates (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """, (key, value))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving template {key}: {e}")
            return False

    def get_template(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a template value."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM bot_templates WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row['value'] if row else default
        except Exception as e:
            logger.error(f"Error fetching template {key}: {e}")
            return default

    # ── Security & Action Logging ──

    def log_admin_action(self, admin_id: int, action: str, result: str) -> bool:
        """Log an administrative action."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                cursor.execute("""
                INSERT INTO admin_logs (admin_id, timestamp, action, result)
                VALUES (?, ?, ?, ?)
                """, (admin_id, now_str, action, result))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
            return False

    def get_admin_logs(self, limit: int = 50) -> List[Dict]:
        """Fetch administrative action logs."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching admin logs: {e}")
            return []

    # ── Rejected Signals Audit & Replay ──

    def insert_rejected_signal(
        self,
        symbol: str,
        direction: str,
        score: int,
        risk_reward: float,
        reason: str,
        details: str = "",
        strategy: str = "SMC/ICT",
        score_components: str = "{}"
    ) -> bool:
        """Record a rejected setup with explicit rationale and individual score components."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Verify column compatibility dynamically for existing DBs
                cursor.execute("PRAGMA table_info(rejected_signals)")
                cols = [c['name'] for c in cursor.fetchall()]
                
                if 'strategy' in cols and 'score_components' in cols:
                    cursor.execute("""
                    INSERT INTO rejected_signals (symbol, strategy, direction, score, score_components, risk_reward, reason, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (symbol, strategy, direction, score, score_components, risk_reward, reason, now_str, details))
                else:
                    cursor.execute("""
                    INSERT INTO rejected_signals (symbol, direction, score, risk_reward, reason, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (symbol, direction, score, risk_reward, reason, now_str, details))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving rejected signal: {e}")
            return False

    def get_rejected_signals(self, limit: int = 50) -> List[Dict]:
        """Fetch historical rejected signal records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM rejected_signals ORDER BY timestamp DESC LIMIT ?", (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching rejected signals: {e}")
            return []

    def get_rejected_signal_by_id(self, rejected_id: int) -> Optional[Dict]:
        """Fetch a specific rejected setup by ID for signal replay inspection."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM rejected_signals WHERE id = ?", (rejected_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching rejected signal {rejected_id}: {e}")
            return None

    # ── Strategy Evaluation & Performance Statistics ──

    def record_strategy_eval(self, strategy_name: str, symbol: str, accepted: bool, score: int, risk_reward: float) -> bool:
        """Record an evaluation event for a strategy."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                cursor.execute("""
                INSERT INTO strategy_evaluations (strategy_name, symbol, timestamp, accepted, score, risk_reward)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (strategy_name, symbol, now_str, 1 if accepted else 0, score, risk_reward))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error recording strategy evaluation: {e}")
            return False

    def get_strategy_statistics(self) -> List[Dict]:
        """Compute live performance statistics for every strategy."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT 
                    strategy_name,
                    COUNT(*) as scanned,
                    SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) as accepted_count,
                    SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END) as rejected_count,
                    AVG(score) as avg_confidence,
                    AVG(risk_reward) as avg_rr
                FROM strategy_evaluations
                GROUP BY strategy_name
                """)
                rows = cursor.fetchall()
                stats = []
                for row in rows:
                    scanned = row['scanned'] or 0
                    acc = row['accepted_count'] or 0
                    rej = row['rejected_count'] or 0
                    rate = (acc / max(1, scanned)) * 100
                    stats.append({
                        'strategy_name': row['strategy_name'],
                        'scanned': scanned,
                        'accepted': acc,
                        'rejected': rej,
                        'acceptance_rate': round(rate, 1),
                        'avg_confidence': round(row['avg_confidence'] or 0.0, 1),
                        'avg_rr': round(row['avg_rr'] or 0.0, 2)
                    })
                return stats
        except Exception as e:
            logger.error(f"Error computing strategy statistics: {e}")
            return []
