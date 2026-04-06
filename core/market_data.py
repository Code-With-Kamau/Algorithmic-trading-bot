"""
core/market_data.py - Market Data Handler
Fetches and processes market data from MT5.
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from utils.logger_config import get_logger

logger = get_logger(__name__)


class MarketData:
    """Handles market data retrieval and preprocessing."""
    
    def __init__(self, settings):
        self.settings = settings
        self.cache = {}  # Simple cache for tick data
        self.cache_duration = 1  # seconds
    
    def get_candles(
        self, 
        symbol: str, 
        timeframe: int, 
        num_bars: int
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV candles from MT5.
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            num_bars: Number of bars to fetch
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            # Fetch rates
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data received for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Rename columns for clarity
            df.columns = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[dict]:
        """
        Get current bid/ask prices.
        
        Returns:
            Dict with 'bid', 'ask', 'spread'
        """
        # Check cache
        cache_key = f"{symbol}_tick"
        if cache_key in self.cache:
            cache_time, cached_data = self.cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < self.cache_duration:
                return cached_data
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            data = {
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': tick.ask - tick.bid,
                'time': datetime.fromtimestamp(tick.time)
            }
            
            # Update cache
            self.cache[cache_key] = (datetime.now(), data)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching tick for {symbol}: {e}")
            return None
    
    def get_symbol_point(self, symbol: str) -> float:
        """Get the point value for a symbol."""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 0.00001  # Default for forex
        return symbol_info.point
    
    def normalize_price(self, symbol: str, price: float) -> float:
        """Normalize price to symbol's digit precision."""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return round(price, 5)
        
        return round(price, symbol_info.digits)
    
    def get_spread_pips(self, symbol: str) -> float:
        """Get current spread in pips."""
        price_data = self.get_current_price(symbol)
        if price_data is None:
            return 0.0
        
        point = self.get_symbol_point(symbol)
        symbol_info = mt5.symbol_info(symbol)
        
        if symbol_info and (symbol_info.digits == 3 or symbol_info.digits == 5):
            pip_value = point * 10
        else:
            pip_value = point
        
        spread_pips = price_data['spread'] / pip_value
        return spread_pips
    
    def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for trading."""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return False
        
        # Check if trading is allowed
        if not symbol_info.trade_mode:
            return False
        
        # Check session times (basic check)
        current_time = datetime.now().time()
        
        # This is simplified - you may want to implement proper session checking
        return True
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_pivot_points(self, df: pd.DataFrame) -> dict:
        """Calculate classic pivot points from previous day."""
        if len(df) < 2:
            return None
        
        prev_high = df['high'].iloc[-2]
        prev_low = df['low'].iloc[-2]
        prev_close = df['close'].iloc[-2]
        
        pivot = (prev_high + prev_low + prev_close) / 3
        
        r1 = 2 * pivot - prev_low
        r2 = pivot + (prev_high - prev_low)
        r3 = prev_high + 2 * (pivot - prev_low)
        
        s1 = 2 * pivot - prev_high
        s2 = pivot - (prev_high - prev_low)
        s3 = prev_low - 2 * (prev_high - pivot)
        
        return {
            'pivot': pivot,
            'r1': r1, 'r2': r2, 'r3': r3,
            's1': s1, 's2': s2, 's3': s3
        }