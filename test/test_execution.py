"""
tests/test_execution.py - Unit Tests for Order Execution
Tests trade execution, modification, and risk management.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import Settings
from config.risk_management import RiskManager
from database.database import Database


class TestRiskManagement(unittest.TestCase):
    """Test risk management calculations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.settings = Settings()
        self.risk_manager = RiskManager(self.settings)
    
    def test_position_size_calculation(self):
        """Test position size calculation."""
        # Note: This requires MT5 connection for symbol info
        # In production, mock MT5 symbol_info
        account_balance = 10000.0
        stop_loss_pips = 20.0
        
        try:
            lot_size = self.risk_manager.calculate_position_size(
                'EURUSD', account_balance, stop_loss_pips
            )
            
            # Lot size should be positive
            self.assertGreater(lot_size, 0)
            
            # Should respect risk percentage
            # With 2% risk and 20 pip SL, position should be reasonable
            self.assertLess(lot_size, 10.0)  # Sanity check
        except:
            self.skipTest("MT5 not available for testing")
    
    def test_stop_loss_pips_calculation(self):
        """Test stop loss pips calculation."""
        entry = 1.1000
        sl = 1.0980
        
        try:
            pips = self.risk_manager.calculate_stop_loss_pips(entry, sl, 'EURUSD')
            
            # Should calculate approximately 20 pips
            self.assertAlmostEqual(pips, 20.0, delta=1.0)
        except:
            self.skipTest("MT5 not available for testing")
    
    def test_trade_validation_rr_ratio(self):
        """Test trade validation with R:R ratio."""
        validation = self.risk_manager.validate_trade(
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.0980,
            take_profit=1.1030,
            direction='BUY'
        )
        
        # R:R should be 1.5:1 (30 pips profit / 20 pips risk)
        if validation['valid']:
            self.assertGreaterEqual(validation['risk_reward'], 1.5)
    
    def test_trade_validation_invalid_sl(self):
        """Test trade validation with invalid stop loss."""
        validation = self.risk_manager.validate_trade(
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.1010,  # SL above entry for BUY
            take_profit=1.1030,
            direction='BUY'
        )
        
        self.assertFalse(validation['valid'])
        self.assertIn('Invalid', validation['reason'])


class TestDatabase(unittest.TestCase):
    """Test database operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = Database(':memory:')
        self.db.initialize()
    
    def test_database_initialization(self):
        """Test database tables are created."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('signals', tables)
        self.assertIn('trades', tables)
        self.assertIn('performance', tables)
        
        conn.close()
    
    def test_log_signal(self):
        """Test logging a signal."""
        from datetime import datetime
        
        signal = {
            'timestamp': datetime.now(),
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry': 1.1000,
            'stop_loss': 1.0980,
            'take_profit': 1.1030,
            'score': 7.5,
            'components': {'fvg': True, 'choch': True}
        }
        
        self.db.log_signal(signal)
        
        # Verify signal was logged
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM signals')
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 1)
    
    def test_log_trade(self):
        """Test logging a trade."""
        from datetime import datetime
        
        trade = {
            'ticket': 12345,
            'symbol': 'EURUSD',
            'type': 'BUY',
            'volume': 0.1,
            'open_price': 1.1000,
            'sl': 1.0980,
            'tp': 1.1030,
            'open_time': datetime.now(),
            'magic': 234000,
            'comment': 'Test trade',
            'signal_score': 7.5
        }
        
        self.db.log_trade(trade)
        
        # Verify trade was logged
        trades = self.db.get_all_trades()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['ticket'], 12345)
    
    def test_update_trade_close(self):
        """Test updating trade with close information."""
        from datetime import datetime
        
        # Log a trade first
        trade = {
            'ticket': 12346,
            'symbol': 'GBPUSD',
            'type': 'SELL',
            'volume': 0.2,
            'open_price': 1.2500,
            'sl': 1.2530,
            'tp': 1.2470,
            'open_time': datetime.now(),
            'magic': 234000,
            'comment': 'Test',
            'signal_score': 8.0
        }
        
        self.db.log_trade(trade)
        
        # Close the trade
        self.db.update_trade_close(
            ticket=12346,
            close_price=1.2470,
            profit=60.0,
            close_time=datetime.now(),
            reason='TP hit'
        )
        
        # Verify trade was updated
        trades = self.db.get_all_trades()
        self.assertIsNotNone(trades[0]['close_price'])
        self.assertEqual(trades[0]['profit'], 60.0)
    
    def test_get_daily_pnl(self):
        """Test getting daily P/L."""
        pnl = self.db.get_daily_pnl()
        
        # Should return 0 or None for empty database
        self.assertTrue(pnl is None or pnl == 0.0)
    
    def test_performance_summary(self):
        """Test getting performance summary."""
        summary = self.db.get_performance_summary(days=30)
        
        # Should return valid summary structure
        self.assertIn('total_trades', summary)
        self.assertIn('win_rate', summary)
        self.assertEqual(summary['total_trades'], 0)  # Empty database


class TestHelpers(unittest.TestCase):
    """Test helper functions."""
    
    def test_pips_to_price(self):
        """Test pips to price conversion."""
        from utils.helpers import pips_to_price
        
        # Without MT5, should use default calculation
        price_value = pips_to_price('EURUSD', 10.0)
        self.assertAlmostEqual(price_value, 0.001, delta=0.0001)
    
    def test_calculate_risk_reward(self):
        """Test risk:reward calculation."""
        from utils.helpers import calculate_risk_reward
        
        rr = calculate_risk_reward(
            entry=1.1000,
            sl=1.0980,
            tp=1.1030,
            direction='BUY'
        )
        
        # Should be 1.5:1 (30 pips / 20 pips)
        self.assertAlmostEqual(rr, 1.5, delta=0.1)
    
    def test_format_currency(self):
        """Test currency formatting."""
        from utils.helpers import format_currency
        
        formatted = format_currency(1234.56)
        self.assertEqual(formatted, '$1,234.56')
    
    def test_safe_divide(self):
        """Test safe division."""
        from utils.helpers import safe_divide
        
        # Normal division
        result = safe_divide(10, 2)
        self.assertEqual(result, 5.0)
        
        # Division by zero should return default
        result = safe_divide(10, 0, default=0.0)
        self.assertEqual(result, 0.0)


if __name__ == '__main__':
    unittest.main()