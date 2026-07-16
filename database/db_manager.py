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
                    trade_data.get('status', 'WAITING_ENTRY'),
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
                    trade_data.get('status', 'WAITING_ENTRY'),
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
        """Fetch all non-terminal trades currently active or pending."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM trades
                WHERE status NOT IN ('TP3_HIT', 'SL_HIT', 'CLOSED', 'CANCELLED')
                ORDER BY created_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching active trades: {e}")
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
