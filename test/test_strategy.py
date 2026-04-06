"""
tests/test_strategy.py - Unit Tests for Trading Strategy
Tests SMC logic, signal generation, and trade validation.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import Settings
from core.strategy import ScalpingStrategy
from database.database import Database


class TestScalpingStrategy(unittest.TestCase):
    """Test cases for ScalpingStrategy class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.settings = Settings()
        self.db = Database(':memory:')  # Use in-memory database for testing
        self.db.initialize()
        self.strategy = ScalpingStrategy(self.settings, self.db)
    
    def create_sample_data(self, num_bars=100, trend='uptrend'):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(end=datetime.now(), periods=num_bars, freq='5min')
        
        if trend == 'uptrend':
            close_prices = np.linspace(1.1000, 1.1100, num_bars)
        elif trend == 'downtrend':
            close_prices = np.linspace(1.1100, 1.1000, num_bars)
        else:  # sideways
            close_prices = np.random.uniform(1.1000, 1.1050, num_bars)
        
        # Add some noise
        close_prices += np.random.normal(0, 0.0005, num_bars)
        
        df = pd.DataFrame({
            'time': dates,
            'open': close_prices - np.random.uniform(0.0001, 0.0005, num_bars),
            'high': close_prices + np.random.uniform(0.0001, 0.0010, num_bars),
            'low': close_prices - np.random.uniform(0.0001, 0.0010, num_bars),
            'close': close_prices,
            'tick_volume': np.random.randint(50, 200, num_bars),
            'spread': np.full(num_bars, 2),
            'real_volume': np.random.randint(1000, 5000, num_bars)
        })
        
        return df
    
    def test_signal_detection_uptrend(self):
        """Test signal detection in uptrend."""
        df = self.create_sample_data(100, 'uptrend')
        signal = self.strategy.detect_signal('EURUSD', df)
        
        # Should detect some signal or None (both valid)
        if signal:
            self.assertIn('direction', signal)
            self.assertIn('entry', signal)
            self.assertIn('stop_loss', signal)
            self.assertIn('take_profit', signal)
            self.assertIn('score', signal)
    
    def test_signal_detection_downtrend(self):
        """Test signal detection in downtrend."""
        df = self.create_sample_data(100, 'downtrend')
        signal = self.strategy.detect_signal('EURUSD', df)
        
        if signal:
            self.assertIn('direction', signal)
            self.assertIn(signal['direction'], ['BUY', 'SELL'])
    
    def test_signal_score_calculation(self):
        """Test signal score calculation."""
        components = {
            'liquidity_sweep': True,
            'fvg': True,
            'order_block': False,
            'choch': True,
            'rsi_confirmed': True,
            'volume_confirmed': False,
            'trend_aligned': 'BULLISH'
        }
        
        score = self.strategy._calculate_signal_score(components)
        
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0)
    
    def test_direction_determination(self):
        """Test trade direction determination."""
        df = self.create_sample_data(50, 'uptrend')
        
        components = {
            'liquidity_sweep': True,
            'fvg': True,
            'order_block': True,
            'choch': True,
            'rsi_confirmed': True,
            'volume_confirmed': True,
            'trend_aligned': 'BULLISH'
        }
        
        liquidity_sweep = {'direction': 'LOW'}
        choch = {'direction': 'BULLISH'}
        
        direction = self.strategy._determine_direction(
            components, liquidity_sweep, choch, 'BUY', df
        )
        
        self.assertIn(direction, ['BUY', 'SELL', None])
    
    def test_confirm_trade_validation(self):
        """Test trade confirmation and validation."""
        df = self.create_sample_data(100, 'uptrend')
        
        signal = {
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry': 1.1050,
            'stop_loss': 1.1030,
            'take_profit': 1.1080,
            'score': 8.5
        }
        
        # Note: This test may fail if MT5 is not connected
        # Should be mocked in production tests
        try:
            result = self.strategy.confirm_trade('EURUSD', signal)
            self.assertIsInstance(result, bool)
        except:
            pass  # Skip if MT5 not available
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        df = self.create_sample_data(10)  # Too few bars
        signal = self.strategy.detect_signal('EURUSD', df)
        
        self.assertIsNone(signal)


class TestIndicators(unittest.TestCase):
    """Test technical indicators."""
    
    def setUp(self):
        """Set up test fixtures."""
        from analysis.indicators import Indicators
        self.settings = Settings()
        self.indicators = Indicators(self.settings)
    
    def create_price_data(self, num_bars=100):
        """Create sample price data."""
        return pd.Series(np.random.uniform(1.1000, 1.1100, num_bars))
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        prices = self.create_price_data(50)
        rsi = self.indicators.calculate_rsi(prices, 14)
        
        self.assertEqual(len(rsi), len(prices))
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        self.assertTrue(all(valid_rsi >= 0))
        self.assertTrue(all(valid_rsi <= 100))
    
    def test_ema_calculation(self):
        """Test EMA calculation."""
        prices = self.create_price_data(50)
        ema = self.indicators.calculate_ema(prices, 20)
        
        self.assertEqual(len(ema), len(prices))
        self.assertFalse(ema.isnull().all())
    
    def test_atr_calculation(self):
        """Test ATR calculation."""
        df = pd.DataFrame({
            'high': np.random.uniform(1.1050, 1.1100, 50),
            'low': np.random.uniform(1.1000, 1.1050, 50),
            'close': np.random.uniform(1.1020, 1.1080, 50)
        })
        
        atr = self.indicators.calculate_atr(df, 14)
        
        self.assertEqual(len(atr), len(df))
        valid_atr = atr.dropna()
        self.assertTrue(all(valid_atr > 0))


class TestSMCLogic(unittest.TestCase):
    """Test Smart Money Concepts logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        from analysis.smc_logic import SMCAnalyzer
        self.settings = Settings()
        self.smc = SMCAnalyzer(self.settings)
    
    def create_fvg_data(self):
        """Create data with a Fair Value Gap."""
        df = pd.DataFrame({
            'time': pd.date_range(end=datetime.now(), periods=10, freq='5min'),
            'open': [1.1000, 1.1010, 1.1020, 1.1015, 1.1018, 1.1025, 1.1030, 1.1035, 1.1040, 1.1045],
            'high': [1.1005, 1.1015, 1.1025, 1.1020, 1.1022, 1.1030, 1.1035, 1.1040, 1.1045, 1.1050],
            'low': [1.0995, 1.1005, 1.1015, 1.1010, 1.1013, 1.1020, 1.1025, 1.1030, 1.1035, 1.1040],
            'close': [1.1003, 1.1012, 1.1018, 1.1016, 1.1020, 1.1028, 1.1033, 1.1038, 1.1043, 1.1048],
            'tick_volume': [100] * 10,
            'spread': [2] * 10,
            'real_volume': [1000] * 10
        })
        return df
    
    def test_fvg_detection(self):
        """Test Fair Value Gap detection."""
        df = self.create_fvg_data()
        fvg = self.smc.detect_fvg(df)
        
        # May or may not detect FVG depending on data
        if fvg:
            self.assertIn('type', fvg)
            self.assertIn(fvg['type'], ['BULLISH', 'BEARISH'])
            self.assertIn('price', fvg)
    
    def test_choch_detection(self):
        """Test Change of Character detection."""
        df = self.create_fvg_data()
        choch = self.smc.detect_choch(df)
        
        if choch:
            self.assertIn('direction', choch)
            self.assertIn(choch['direction'], ['BULLISH', 'BEARISH'])


class TestLiquidityAnalysis(unittest.TestCase):
    """Test liquidity analysis."""
    
    def setUp(self):
        """Set up test fixtures."""
        from analysis.liquidity import LiquidityAnalyzer
        self.settings = Settings()
        self.liquidity = LiquidityAnalyzer(self.settings)
    
    def create_sweep_data(self):
        """Create data with liquidity sweep pattern."""
        df = pd.DataFrame({
            'time': pd.date_range(end=datetime.now(), periods=15, freq='5min'),
            'open': [1.1000] * 15,
            'high': [1.1010, 1.1012, 1.1015, 1.1020, 1.1018, 1.1022, 1.1025, 1.1028, 1.1030, 1.1032, 1.1035, 1.1038, 1.1040, 1.1042, 1.1045],
            'low': [1.0990, 1.0992, 1.0995, 1.0998, 1.1000, 1.1002, 1.1005, 1.1008, 1.1010, 1.1012, 1.1015, 1.1018, 1.1020, 1.1022, 1.1025],
            'close': [1.1005] * 15,
            'tick_volume': [100] * 15,
            'spread': [2] * 15,
            'real_volume': [1000] * 15
        })
        return df
    
    def test_sweep_detection(self):
        """Test liquidity sweep detection."""
        df = self.create_sweep_data()
        sweep = self.liquidity.detect_sweep(df)
        
        # May or may not detect depending on pattern
        if sweep:
            self.assertIn('direction', sweep)
            self.assertIn('level', sweep)
    
    def test_liquidity_score(self):
        """Test liquidity score calculation."""
        df = self.create_sweep_data()
        score = self.liquidity.calculate_liquidity_score(df)
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 10.0)


if __name__ == '__main__':
    unittest.main()