"""
config/settings.py - Trading Bot Configuration
Centralized configuration management using environment variables.
"""

import os
from typing import List
import MetaTrader5 as mt5


class Settings:
    """Global settings and configuration."""
    
    def __init__(self):
        # MT5 Connection
        self.MT5_LOGIN = int(os.getenv('MT5_LOGIN', 'your account'))
        self.MT5_PASSWORD = os.getenv('MT5_PASSWORD', 'your password')
        self.MT5_SERVER = os.getenv('MT5_SERVER', 'mt5-demo01.pepperstone.com')
        
        # Trading Symbols
        self.SYMBOLS = os.getenv('SYMBOLS', 'EURUSD,GBPUSD,USDJPY,XAUUSD,USDCAD,EURCHF').split(',')
        
        # Timeframe Settings
        self.TIMEFRAME = self._parse_timeframe(os.getenv('TIMEFRAME', 'M5'))
        self.LOOKBACK_BARS = int(os.getenv('LOOKBACK_BARS', '200'))
        self.MIN_BARS_REQUIRED = int(os.getenv('MIN_BARS_REQUIRED', '50'))
        
        # Risk Management (from risk_management.py)
        self.RISK_PERCENT = float(os.getenv('RISK_PERCENT', '2.0'))
        self.MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', '5.0'))
        self.MAX_OPEN_TRADES = int(os.getenv('MAX_OPEN_TRADES', '5'))
        self.MIN_RISK_REWARD = float(os.getenv('MIN_RISK_REWARD', '1.5'))
        
        # Strategy Parameters
        self.RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
        self.RSI_OVERBOUGHT = int(os.getenv('RSI_OVERBOUGHT', '70'))
        self.RSI_OVERSOLD = int(os.getenv('RSI_OVERSOLD', '30'))
        
        self.ATR_PERIOD = int(os.getenv('ATR_PERIOD', '14'))
        self.ATR_MULTIPLIER = float(os.getenv('ATR_MULTIPLIER', '1.5'))
        
        # SMC Parameters
        self.FVG_MIN_SIZE = float(os.getenv('FVG_MIN_SIZE', '0.0001'))  # Minimum FVG size in price
        self.ORDER_BLOCK_LOOKBACK = int(os.getenv('ORDER_BLOCK_LOOKBACK', '20'))
        self.LIQUIDITY_SWEEP_PIPS = float(os.getenv('LIQUIDITY_SWEEP_PIPS', '5.0'))
        
        # Trade Management
        self.USE_TRAILING_STOP = os.getenv('USE_TRAILING_STOP', 'True').lower() == 'true'
        self.TRAILING_STOP_PIPS = float(os.getenv('TRAILING_STOP_PIPS', '10.0'))
        self.BREAKEVEN_PIPS = float(os.getenv('BREAKEVEN_PIPS', '10.0'))
        self.PARTIAL_CLOSE_PERCENT = float(os.getenv('PARTIAL_CLOSE_PERCENT', '50.0'))
        self.PARTIAL_CLOSE_AT_RR = float(os.getenv('PARTIAL_CLOSE_AT_RR', '1.0'))
        
        # System Settings
        self.LOOP_DELAY = float(os.getenv('LOOP_DELAY', '1.0'))  # Seconds between loop iterations
        self.MAX_SLIPPAGE = int(os.getenv('MAX_SLIPPAGE', '5'))  # Points
        
        # Logging
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'logs/trading_bot.log')
        
        # Database
        self.DB_PATH = os.getenv('DB_PATH', 'database/trades.db')
    
    @staticmethod
    def _parse_timeframe(tf_str: str) -> int:
        """Convert timeframe string to MT5 constant."""
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        return timeframe_map.get(tf_str, mt5.TIMEFRAME_M5)
    
    def get_symbol_info(self, symbol: str) -> dict:
        """Get symbol specifications."""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return None
        
        return {
            'point': symbol_info.point,
            'digits': symbol_info.digits,
            'trade_contract_size': symbol_info.trade_contract_size,
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step,
        }