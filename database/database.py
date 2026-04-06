"""
database/database.py - Database Management
Handles SQLite operations for signals, trades, and analytics.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from utils.logger_config import get_logger

logger = get_logger(__name__)


class Database:
    """SQLite database manager for trading data."""
    
    def __init__(self, db_path: str = 'database/trades.db'):
        self.db_path = db_path
        self.ensure_directory()
    
    def ensure_directory(self):
        """Ensure database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def initialize(self):
        """Initialize database tables."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Signals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    score REAL NOT NULL,
                    components TEXT,
                    executed BOOLEAN DEFAULT 0
                )
            ''')
            
            # Trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER UNIQUE NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    type VARCHAR(10) NOT NULL,
                    volume REAL NOT NULL,
                    open_price REAL NOT NULL,
                    close_price REAL,
                    sl REAL NOT NULL,
                    tp REAL NOT NULL,
                    open_time DATETIME NOT NULL,
                    close_time DATETIME,
                    profit REAL,
                    magic INTEGER,
                    comment TEXT,
                    signal_score REAL,
                    close_reason TEXT
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0
                )
            ''')
            
            # System logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    level VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
    
    def log_signal(self, signal: Dict):
        """Log a trading signal."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO signals (timestamp, symbol, direction, entry_price, 
                                   stop_loss, take_profit, score, components)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal['timestamp'],
                signal['symbol'],
                signal['direction'],
                signal['entry'],
                signal['stop_loss'],
                signal['take_profit'],
                signal['score'],
                str(signal.get('components', {}))
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging signal: {e}")
    
    def log_trade(self, trade: Dict):
        """Log a new trade."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (ticket, symbol, type, volume, open_price, 
                                  sl, tp, open_time, magic, comment, signal_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade['ticket'],
                trade['symbol'],
                trade['type'],
                trade['volume'],
                trade['open_price'],
                trade['sl'],
                trade['tp'],
                trade['open_time'],
                trade['magic'],
                trade.get('comment', ''),
                trade.get('signal_score', 0)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Trade {trade['ticket']} logged to database")
            
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    def update_trade_close(self, ticket: int, close_price: float, 
                          profit: float, close_time: datetime, reason: str):
        """Update trade with close information."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE trades 
                SET close_price = ?, profit = ?, close_time = ?, close_reason = ?
                WHERE ticket = ?
            ''', (close_price, profit, close_time, reason, ticket))
            if cursor.rowcount==0:
                logger.warning(f"No trade found with ticket {ticket} to update close info.")
            conn.commit()
            conn.close()
            
            # Update daily performance
            self._update_daily_performance(close_time.date(), profit)
            
        except Exception as e:
            logger.error(f"Error updating trade close: {e}", exc_info=True)
    
    def _update_daily_performance(self, date, profit: float):
        """Update daily performance metrics."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if record exists
            cursor.execute('SELECT * FROM performance WHERE date = ?', (date,))
            record = cursor.fetchone()
            
            if record:
                cursor.execute('''
                    UPDATE performance 
                    SET total_trades = total_trades + 1,
                        winning_trades = winning_trades + ?,
                        losing_trades = losing_trades + ?,
                        total_profit = total_profit + ?
                    WHERE date = ?
                ''', (
                    1 if profit > 0 else 0,
                    1 if profit < 0 else 0,
                    profit,
                    date
                ))
            else:
                cursor.execute('''
                    INSERT INTO performance (date, total_trades, winning_trades, 
                                           losing_trades, total_profit)
                    VALUES (?, 1, ?, ?, ?)
                ''', (
                    date,
                    1 if profit > 0 else 0,
                    1 if profit < 0 else 0,
                    profit
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating daily performance: {e}")
    
    def get_daily_pnl(self) -> Optional[float]:
        """Get today's profit/loss."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            today = datetime.now().date()
            cursor.execute('''
                SELECT SUM(profit) FROM trades 
                WHERE DATE(close_time) = ? AND close_time IS NOT NULL
            ''', (today,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result[0] is not None else 0.0
            
        except Exception as e:
            logger.error(f"Error getting daily PnL: {e}")
            return None
    
    def get_all_trades(self, limit: int = 100) -> List[Dict]:
        """Get all trades from database."""
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY open_time DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_open_trades(self) -> List[Dict]:
        """Get currently open trades."""
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM trades WHERE close_time IS NULL')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get performance summary for last N days."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            start_date = (datetime.now() - timedelta(days=days)).date()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losers,
                    SUM(profit) as total_profit,
                    AVG(profit) as avg_profit,
                    MAX(profit) as max_win,
                    MIN(profit) as max_loss
                FROM trades
                WHERE DATE(close_time) >= ? AND close_time IS NOT NULL
            ''', (start_date,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] > 0:
                return {
                    'total_trades': result[0],
                    'winners': result[1] or 0,
                    'losers': result[2] or 0,
                    'win_rate': (result[1] or 0) / result[0] * 100,
                    'total_profit': result[3] or 0,
                    'avg_profit': result[4] or 0,
                    'max_win': result[5] or 0,
                    'max_loss': result[6] or 0
                }
            else:
                return {
                    'total_trades': 0,
                    'winners': 0,
                    'losers': 0,
                    'win_rate': 0,
                    'total_profit': 0,
                    'avg_profit': 0,
                    'max_win': 0,
                    'max_loss': 0
                }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 31):
        """Clean up old signals and logs."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('DELETE FROM signals WHERE timestamp < ?', (cutoff_date,))
            cursor.execute('DELETE FROM system_logs WHERE timestamp < ?', (cutoff_date,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up data older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    def manual_cleanup(self, days: int = 90) -> dict:
        """
        Manual database cleanup with statistics.
        
        Args:
            days: Keep data newer than this many days
            
        Returns:
            Dict with cleanup statistics
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Count records before cleanup
            cursor.execute('SELECT COUNT(*) FROM signals WHERE timestamp < ?', (cutoff_date,))
            signals_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM system_logs WHERE timestamp < ?', (cutoff_date,))
            logs_count = cursor.fetchone()[0]
            
            # Keep all trades (don't delete), but can delete old signals and logs
            cursor.execute('DELETE FROM signals WHERE timestamp < ?', (cutoff_date,))
            cursor.execute('DELETE FROM system_logs WHERE timestamp < ?', (cutoff_date,))
            
            # Vacuum database to reclaim space
            cursor.execute('VACUUM')
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'signals_deleted': signals_count,
                'logs_deleted': logs_count,
                'cutoff_days': days
            }
            
        except Exception as e:
            logger.error(f"Error in manual cleanup: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_database_stats(self) -> dict:
        """Get database statistics."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM signals')
            signals_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM trades')
            trades_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM trades WHERE close_time IS NULL')
            open_trades_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM system_logs')
            logs_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_signals': signals_count,
                'total_trades': trades_count,
                'open_trades': open_trades_count,
                'system_logs': logs_count
            }
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}